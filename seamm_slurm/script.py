# -*- coding: utf-8 -*-

"""Build a full ``sbatch`` script from a directives dict and a payload.

Matches the ``<root>/<jobserver-name>.ini`` config shape used by
``seamm_jobserver`` (see ``~/Work/SEAMM/jobserver-slurm-plan.md``): each
cluster/queue section's keys (``partition``, ``account``, ``qos``, ``nodes``,
``ntasks``, ``time``, ``mem``, ``gpus``, ...) map directly to ``#SBATCH``
directives here. A blank/``None`` value means "don't pass that directive" --
let SLURM's own defaults apply.
"""

# Directive keys with a dedicated, human-friendly name (rather than the
# literal `--flag` spelling) and the #SBATCH flag they map to. Order here is
# the order they're emitted in, for reproducible script text.
_DIRECTIVE_FLAGS = {
    "job_name": "--job-name",
    "partition": "--partition",
    "account": "--account",
    "qos": "--qos",
    "nodes": "--nodes",
    "ntasks": "--ntasks",
    "cpus_per_task": "--cpus-per-task",
    "time": "--time",
    "mem": "--mem",
    "gpus": "--gpus",
    "output": "--output",
    "error": "--error",
    "chdir": "--chdir",
}


def build_script(directives, payload, *, shell="/bin/bash"):
    """Build a full sbatch script: shebang, ``#SBATCH`` lines, then payload.

    Parameters
    ----------
    directives : dict(str, any)
        SLURM submission options, keyed by the plain names in
        ``_DIRECTIVE_FLAGS`` (e.g. ``"partition"``, not ``"--partition"``).
        A key with a blank string or ``None`` value is skipped -- not passed
        to ``sbatch`` at all. Keys not in ``_DIRECTIVE_FLAGS`` are passed
        through as-is, converting underscores to dashes (e.g.
        ``{"gres": "gpu:1"}`` -> ``#SBATCH --gres=gpu:1``), so a
        ``<root>/<jobserver-name>.ini`` section can carry SLURM options this
        module doesn't special-case without any code change here.
    payload : str
        The body of the script -- the actual commands to run (conda
        activation, then the job's command line). Used verbatim, after the
        ``#SBATCH`` block.
    shell : str = "/bin/bash"
        The shebang interpreter.

    Returns
    -------
    str
        The full script text, ready to hand to ``SlurmBackend.submit()``.
    """
    lines = [f"#!{shell}"]

    seen = set()
    for key, flag in _DIRECTIVE_FLAGS.items():
        seen.add(key)
        value = directives.get(key)
        if value in (None, ""):
            continue
        lines.append(f"#SBATCH {flag}={value}")

    for key, value in directives.items():
        if key in seen or value in (None, ""):
            continue
        flag = "--" + key.replace("_", "-")
        lines.append(f"#SBATCH {flag}={value}")

    lines.append("")
    lines.append(payload.rstrip("\n"))
    lines.append("")

    return "\n".join(lines)
