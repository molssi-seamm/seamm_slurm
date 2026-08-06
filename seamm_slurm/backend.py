# -*- coding: utf-8 -*-

"""``SlurmBackend``: shared submit/poll/cancel logic for talking to SLURM.

Subclasses (``LocalSlurm``, ``SshSlurm``) only need to implement ``_run`` --
how to actually execute a SLURM CLI command (locally, or over SSH). Command
construction, the JSON-vs-text fallback (not every SLURM version supports
``squeue --json``/``sacct --json`` -- confirmed during Phase 0 groundwork:
SLURM 21.08.5 has it, SLURM 20.11.4 doesn't), and output parsing all live
here once, so both transports behave identically.
"""

import json
import logging
from abc import ABC, abstractmethod

from .status import JobStatus, classify

logger = logging.getLogger("seamm_slurm")


class SlurmError(RuntimeError):
    """Raised when a SLURM CLI command fails unexpectedly."""


class SlurmSubmitError(SlurmError):
    """Raised when ``sbatch`` fails to submit a job."""


class SlurmBackend(ABC):
    """Talks to a SLURM cluster's ``sbatch``/``squeue``/``sacct``/``scancel``,
    via some transport."""

    def __init__(self):
        # Tri-state: None = not yet probed, True/False = known support.
        self._squeue_json = None
        self._sacct_json = None

    # ---- transport hook, implemented by subclasses ----------------------
    @abstractmethod
    def _run(self, argv, input_text=None):
        """Run a SLURM CLI command.

        Parameters
        ----------
        argv : [str]
            The command and its arguments, e.g. ``["sbatch", "--parsable"]``.
        input_text : str or None
            Text to feed on the command's stdin (used for ``sbatch``, which
            reads the script from stdin when no script file is given).

        Returns
        -------
        (int, str, str)
            ``(returncode, stdout, stderr)``.
        """

    # ---- public API -------------------------------------------------------
    def submit(self, script, *, job_name=None):
        """Submit a script (its full text, including any ``#SBATCH`` lines
        and shebang -- see ``seamm_slurm.script.build_script``) via
        ``sbatch --parsable``, fed on stdin. Never needs the script to exist
        as a file the target host can see.

        Returns
        -------
        str
            The SLURM job ID.
        """
        argv = ["sbatch", "--parsable"]
        if job_name:
            argv += ["--job-name", job_name]
        rc, out, err = self._run(argv, input_text=script)
        if rc != 0:
            raise SlurmSubmitError(f"sbatch failed ({rc}): {err.strip()}")
        # --parsable prints "<jobid>" or "<jobid>;<cluster>"
        lines = [line for line in out.strip().splitlines() if line.strip()]
        if not lines:
            raise SlurmSubmitError(f"sbatch returned no job id: {out!r} {err!r}")
        job_id = lines[-1].split(";")[0].strip()
        if not job_id:
            raise SlurmSubmitError(f"sbatch returned no job id: {out!r} {err!r}")
        return job_id

    def cancel(self, job_id):
        """Cancel a submitted job."""
        rc, out, err = self._run(["scancel", str(job_id)])
        if rc != 0:
            raise SlurmError(f"scancel {job_id} failed ({rc}): {err.strip()}")

    def poll_many(self, job_ids):
        """Get the current status of a batch of jobs, in as few SLURM CLI
        calls as possible (one ``squeue`` call, plus one ``sacct`` call for
        anything ``squeue`` no longer lists).

        Parameters
        ----------
        job_ids : [str]
            The SLURM job IDs to check.

        Returns
        -------
        {str: JobStatus}
            Keyed by job ID. A job ID that SLURM has no record of at all
            (e.g. purged from accounting) is simply absent from the result;
            callers should treat "missing" the same as "can't confirm this
            job still exists".
        """
        job_ids = [str(j) for j in job_ids]
        if not job_ids:
            return {}

        result = self._squeue(job_ids)

        missing = [j for j in job_ids if j not in result]
        if missing:
            result.update(self._sacct(missing))

        return result

    # ---- squeue -----------------------------------------------------------
    def _squeue(self, job_ids):
        ids = ",".join(job_ids)

        if self._squeue_json is not False:
            rc, out, err = self._run(["squeue", "--json", "--jobs", ids])
            if rc == 0:
                self._squeue_json = True
                try:
                    return self._parse_squeue_json(out)
                except (ValueError, KeyError) as e:
                    logger.warning(f"Could not parse squeue --json output: {e}")
                    return {}
            if _is_unrecognized_option(err):
                self._squeue_json = False
            else:
                # Transient/other failure (e.g. all the ids are already gone)
                # -- not a hard error, just nothing to report from squeue.
                return {}

        fmt = "%i|%T|%R"
        rc, out, err = self._run(
            ["squeue", "--noheader", f"--format={fmt}", "--jobs", ids]
        )
        if rc != 0:
            return {}
        return self._parse_squeue_text(out)

    @staticmethod
    def _parse_squeue_json(out):
        data = json.loads(out)
        result = {}
        for j in data.get("jobs", []):
            job_id = str(j["job_id"])
            state = j.get("job_state", "")
            if isinstance(state, list):
                # Some SLURM/OpenAPI versions report job_state as a list of
                # flags rather than a single string.
                state = state[0] if state else ""
            result[job_id] = JobStatus(
                job_id=job_id,
                state=state,
                category=classify(state),
                raw=j,
            )
        return result

    @staticmethod
    def _parse_squeue_text(out):
        result = {}
        for line in out.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split("|")
            if len(parts) < 2:
                continue
            job_id, state = parts[0].strip(), parts[1].strip()
            reason = parts[2].strip() if len(parts) > 2 else None
            result[job_id] = JobStatus(
                job_id=job_id,
                state=state,
                category=classify(state),
                reason=reason,
            )
        return result

    # ---- sacct --------------------------------------------------------------
    def _sacct(self, job_ids):
        ids = ",".join(job_ids)

        if self._sacct_json is not False:
            rc, out, err = self._run(["sacct", "--json", "--jobs", ids])
            if rc == 0:
                self._sacct_json = True
                try:
                    return self._parse_sacct_json(out)
                except (ValueError, KeyError) as e:
                    logger.warning(f"Could not parse sacct --json output: {e}")
                    return {}
            if _is_unrecognized_option(err):
                self._sacct_json = False
            else:
                return {}

        fmt = "JobID,State,ExitCode"
        rc, out, err = self._run(
            ["sacct", "--parsable2", "--noheader", f"--format={fmt}", "--jobs", ids]
        )
        if rc != 0:
            return {}
        return self._parse_sacct_text(out)

    @staticmethod
    def _parse_sacct_json(out):
        data = json.loads(out)
        result = {}
        for j in data.get("jobs", []):
            job_id = str(j["job_id"])
            state_field = j.get("state", {})
            if isinstance(state_field, dict):
                state = state_field.get("current", "")
                reason = state_field.get("reason")
            else:
                # Fall back gracefully if a SLURM version reports state as a
                # plain string here too.
                state = state_field
                reason = None
            if isinstance(state, list):
                state = state[0] if state else ""
            exit_field = j.get("exit_code", {})
            exit_code = (
                exit_field.get("return_code")
                if isinstance(exit_field, dict)
                else exit_field
            )
            result[job_id] = JobStatus(
                job_id=job_id,
                state=state,
                category=classify(state),
                exit_code=exit_code,
                reason=reason,
                raw=j,
            )
        return result

    @staticmethod
    def _parse_sacct_text(out):
        result = {}
        for line in out.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split("|")
            if len(parts) < 2:
                continue
            job_id, state = parts[0].strip(), parts[1].strip()
            # Sub-step rows (e.g. "123.batch", "123.extern") describe pieces
            # of the job, not the job itself -- skip them.
            if "." in job_id:
                continue
            exit_code = parts[2].strip() if len(parts) > 2 else None
            result[job_id] = JobStatus(
                job_id=job_id,
                state=state,
                category=classify(state),
                exit_code=exit_code,
            )
        return result


def _is_unrecognized_option(stderr):
    stderr = stderr.lower()
    return "unrecognized option" in stderr or "invalid option" in stderr
