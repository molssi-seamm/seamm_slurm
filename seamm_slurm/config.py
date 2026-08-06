# -*- coding: utf-8 -*-

"""Load a JobServer's ``<root>/<jobserver-name>.ini`` SLURM/queue config.

System/machine config, not a user preference -- lives at ``<root>``
(``~/SEAMM`` by default), alongside ``orca.ini``/``lammps.ini``/
``dashboards.ini``, not in ``~/.seamm.d/seamm.ini``. Named after the
JobServer instance (its ``--name``, default hostname) rather than a fixed
``slurm.ini``, since a JobServer may eventually route jobs to more than one
cluster/queue -- one section per cluster/queue target.

Lives in ``seamm_slurm`` (not ``seamm_jobserver``, where it started) so any
dependency-light consumer -- ``seamm_jobserver`` today, a future
``seamm_webui`` job-submission UI, a future ``seamm_exec`` per-step executor
-- can read/validate this file without pulling in the rest of the SEAMM
stack. See ``seamm_jobserver``'s ``docs/developer_guide/campaigns/
2026-08-05/`` for the full design.
"""

import configparser
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .local import LocalSlurm
from .ssh import SshSlurm

# Section keys that describe JobServer-side behavior rather than a SLURM
# submission directive -- not forwarded to seamm_slurm.script.build_script.
_NON_DIRECTIVE_KEYS = {
    "type",
    "transport",
    "host",
    "max_concurrent_jobs",
    "max_resubmits",
    "default",
}


@dataclass
class FieldLimits:
    """Constraints on a per-job override of one SLURM directive.

    All fields optional: a directive can be listed as overridable with no
    constraint at all, meaning "any value SLURM itself accepts."
    """

    choices: Optional[list] = None
    minimum: Optional[str] = None
    maximum: Optional[str] = None


@dataclass
class SlurmSection:
    """One cluster/queue target from a ``<root>/<jobserver-name>.ini`` file."""

    name: str
    transport: str
    host: Optional[str]
    directives: dict = field(default_factory=dict)
    max_concurrent_jobs: int = 20
    max_resubmits: int = 3
    limits: dict = field(default_factory=dict)  # {directive: FieldLimits}

    def build_backend(self):
        """Construct the ``seamm_slurm`` backend this section describes."""
        if self.transport == "local":
            return LocalSlurm()
        elif self.transport == "ssh":
            if not self.host:
                raise RuntimeError(
                    f"SLURM section '{self.name}' has transport=ssh but no " "host set"
                )
            return SshSlurm(self.host)
        else:
            raise RuntimeError(
                f"SLURM section '{self.name}' has unknown transport "
                f"'{self.transport}' (expected 'local' or 'ssh')"
            )

    def merge_overrides(self, requested):
        """Merge a job's requested per-directive overrides on top of this
        section's defaults, validating each against ``self.limits``.

        Parameters
        ----------
        requested : dict(str, any)
            Directive overrides a job asked for, e.g. ``{"ntasks": 4}`` --
            typically a job's ``parameters["slurm"]`` (minus any non-directive
            keys such as a future cluster-routing ``"section"``).

        Returns
        -------
        dict
            The final directives dict (this section's defaults with the
            validated overrides applied), ready for
            ``seamm_slurm.script.build_script``.

        Raises
        ------
        ValueError
            If a requested field isn't overridable for this section, or its
            value is outside the configured choices/bounds. Never trust a
            caller (e.g. a web UI) to have already enforced this --
            validate here regardless of what constrained the request's
            origin.
        """
        directives = dict(self.directives)
        for key, value in requested.items():
            limits = self.limits.get(key)
            if limits is None:
                raise ValueError(
                    f"'{key}' is not an overridable SLURM directive for "
                    f"section '{self.name}'"
                )
            if limits.choices is not None and str(value) not in limits.choices:
                raise ValueError(
                    f"'{key}={value}' is not one of the allowed choices for "
                    f"section '{self.name}': {limits.choices}"
                )
            if limits.minimum is not None or limits.maximum is not None:
                parsed = _parse_slurm_value(key, value)
                if limits.minimum is not None:
                    lo = _parse_slurm_value(key, limits.minimum)
                    if parsed < lo:
                        raise ValueError(
                            f"'{key}={value}' is below the minimum "
                            f"({limits.minimum}) for section '{self.name}'"
                        )
                if limits.maximum is not None:
                    hi = _parse_slurm_value(key, limits.maximum)
                    if parsed > hi:
                        raise ValueError(
                            f"'{key}={value}' exceeds the maximum "
                            f"({limits.maximum}) for section '{self.name}'"
                        )
            directives[key] = value
        return directives


def load_slurm_config(root, jobserver_name, section=None):
    """Load ``<root>/<jobserver_name>.ini``, if it exists.

    Parameters
    ----------
    root : str or Path
        The SEAMM root directory (e.g. ``~/SEAMM``), same as every other
        per-code ``.ini`` file.
    jobserver_name : str
        This JobServer instance's ``--name`` (default: hostname).
    section : str or None
        Which section to use. If ``None``, uses ``[DEFAULT]``'s
        ``default =`` key, falling back to the sole section if there is
        exactly one and no ``default`` is set.

    Returns
    -------
    SlurmSection or None
        ``None`` means "no such file" -- the caller should fall back to
        running jobs as local subprocesses, exactly as if this feature did
        not exist.
    """
    ini_path = Path(root).expanduser() / f"{jobserver_name}.ini"
    if not ini_path.exists():
        return None

    config = configparser.ConfigParser(interpolation=None)
    config.read(ini_path)

    if section is None:
        section = config.defaults().get("default")
    if section is None:
        # A ".limits" section is a companion, not a routable target itself.
        candidates = [s for s in config.sections() if not s.endswith(".limits")]
        if len(candidates) == 1:
            section = candidates[0]
        else:
            raise RuntimeError(
                f"{ini_path} has no [DEFAULT] default= and no single, "
                "unambiguous section to use."
            )
    if section not in config:
        raise RuntimeError(f"{ini_path} has no section '{section}'")

    items = dict(config.items(section))

    transport = items.get("transport", "local")
    host = items.get("host") or None
    max_concurrent_jobs = int(items.get("max_concurrent_jobs", 20))
    max_resubmits = int(items.get("max_resubmits", 3))

    directives = {
        k: v for k, v in items.items() if k not in _NON_DIRECTIVE_KEYS and v != ""
    }

    limits = _load_limits(config, section)

    return SlurmSection(
        name=section,
        transport=transport,
        host=host,
        directives=directives,
        max_concurrent_jobs=max_concurrent_jobs,
        max_resubmits=max_resubmits,
        limits=limits,
    )


def _load_limits(config, section):
    """Parse the optional ``[<section>.limits]`` companion section.

    Secure by default: absent entirely means nothing is overridable.
    """
    limits_section = f"{section}.limits"
    if limits_section not in config:
        return {}

    items = dict(config.items(limits_section))
    # dict(config.items(...)) inherits [DEFAULT] keys too (e.g. "default")
    items.pop("default", None)

    overridable_raw = items.pop("overridable", "")
    overridable = [f.strip() for f in overridable_raw.split(",") if f.strip()]

    per_field = {}
    for key, value in items.items():
        if "." not in key:
            continue
        field_name, attr = key.rsplit(".", 1)
        if attr not in ("choices", "min", "max"):
            continue
        per_field.setdefault(field_name, {})[attr] = value

    limits = {}
    for field_name in overridable:
        attrs = per_field.get(field_name, {})
        choices = None
        if "choices" in attrs:
            choices = [c.strip() for c in attrs["choices"].split(",") if c.strip()]
        limits[field_name] = FieldLimits(
            choices=choices,
            minimum=attrs.get("min"),
            maximum=attrs.get("max"),
        )
    return limits


# Known unit-aware SLURM directive names -- everything else is compared as a
# plain number. Not a general SLURM-value-type system, just what's needed
# for the directives sites actually bound today (see FieldLimits/.limits).
_SIZE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*([KMGT]?)", re.IGNORECASE)
_SIZE_MULTIPLIER_MB = {"": 1, "K": 1 / 1024, "M": 1, "G": 1024, "T": 1024 * 1024}


def _parse_size(value):
    """Parse a SLURM-style memory size (e.g. ``"100G"``, ``"2048"``,
    ``"20000M"``) into MB -- SLURM's own default unit for ``--mem`` when no
    suffix is given."""
    match = _SIZE_RE.fullmatch(str(value).strip())
    if not match:
        raise ValueError(f"cannot parse SLURM size value: {value!r}")
    number, suffix = match.groups()
    return float(number) * _SIZE_MULTIPLIER_MB[suffix.upper()]


def _parse_time(value):
    """Parse a SLURM time value (``"04:00:00"``, ``"1-04:00:00"``, or a bare
    minute count) into seconds."""
    text = str(value).strip()
    days = 0
    if "-" in text:
        days_str, text = text.split("-", 1)
        days = int(days_str)
    parts = [int(p) for p in text.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    hours, minutes, seconds = parts[-3:]
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def _parse_slurm_value(field_name, value):
    """Parse a directive value into a comparable float."""
    if field_name == "mem":
        return _parse_size(value)
    if field_name == "time":
        return _parse_time(value)
    return float(value)
