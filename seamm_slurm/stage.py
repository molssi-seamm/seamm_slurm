# -*- coding: utf-8 -*-

"""Stage a job's working directory to/from a remote host.

Needed when a JobServer's ``transport = ssh`` points at a host that shares
no filesystem with the JobServer itself -- unlike every case validated so
far, where the JobServer runs on (or already shares storage with) the
SLURM submit host. Paired with the transport the same way
``LocalSlurm``/``SshSlurm`` are: ``LocalStager`` for the shared-storage
case (a no-op) and ``RsyncStager`` for the no-shared-filesystem case.

Lives here, not in ``seamm_jobserver``, for the same reason ``config.py``
does: a lightweight consumer should be able to use the transport without
pulling in the rest of ``seamm_jobserver`` (psutil, GUI code, job-running
machinery). See ``seamm_jobserver``'s ``docs/developer_guide/campaigns/
2026-08-05/`` (Phase 8) for the full design this implements.
"""

import shlex
import subprocess
from abc import ABC, abstractmethod


class StageError(RuntimeError):
    """Raised when staging a job's files to or from a remote host fails."""


class JobStager(ABC):
    """Moves a job's working directory to/from wherever it actually needs
    to run."""

    @abstractmethod
    def stage_in(self, local_wdir, remote_wdir):
        """Make ``remote_wdir`` ready to run the job, from ``local_wdir``.

        Returns the working directory the job should actually use (for the
        ``#SBATCH --chdir`` directive, and for the job's own command line)
        -- ``local_wdir`` itself for ``LocalStager``, ``remote_wdir`` for
        ``RsyncStager``.
        """

    @abstractmethod
    def stage_out(self, remote_wdir, local_wdir):
        """Pull a finished job's files back, so ``job_data.json`` and the
        flowchart's results land in ``local_wdir`` where the JobServer
        (and the dashboard) can see them. No-op for ``LocalStager``."""


class LocalStager(JobStager):
    """No-op: the JobServer already shares storage with the SLURM submit
    host (every case validated so far), so there's nothing to move."""

    def stage_in(self, local_wdir, remote_wdir):
        return local_wdir

    def stage_out(self, remote_wdir, local_wdir):
        pass


class RsyncStager(JobStager):
    """Pushes/pulls a job's working directory to/from a remote host with no
    shared filesystem, over ``rsync -e ssh``. Assumes the same
    passwordless SSH access ``SshSlurm`` does.

    A job's working directory is already self-contained by the time a
    JobServer picks it up: ``flowchart.flow``, the ``job_data.json`` stub,
    and a ``data/`` directory holding every file the flowchart references
    -- SEAMM's existing ``type: "file"`` control-parameter mechanism
    (``seamm_dashboard_client.dashboard.Dashboard.submit()`` +
    ``safe_filename()``) already stages those into ``data/`` and rewrites
    the command line to ``job:data/...`` at submission time, before this
    ever runs. So staging is just "copy the whole directory," not a
    general arbitrary-path resolver.

    Known limitation, not handled here: a ``job://<n>/...`` cross-job file
    reference (e.g. a restart checkpoint from another job) points outside
    the referencing job's own working directory, so it isn't staged --
    such a reference in a job routed through this stager will fail to
    resolve on the remote host.
    """

    def __init__(self, host, *, ssh_command="ssh", rsync_command="rsync"):
        self.host = host
        self.ssh_command = ssh_command
        self.rsync_command = rsync_command

    def stage_in(self, local_wdir, remote_wdir):
        self._run_ssh(["mkdir", "-p", str(remote_wdir)])
        self._rsync(f"{local_wdir}/", f"{self.host}:{remote_wdir}/")
        return remote_wdir

    def stage_out(self, remote_wdir, local_wdir):
        self._rsync(f"{self.host}:{remote_wdir}/", f"{local_wdir}/")

    def _run_ssh(self, argv):
        remote_cmd = " ".join(shlex.quote(a) for a in argv)
        proc = subprocess.run(
            [self.ssh_command, self.host, remote_cmd],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise StageError(
                f"{self.ssh_command} {self.host} {remote_cmd!r} failed "
                f"({proc.returncode}): {proc.stderr.strip()}"
            )

    def _rsync(self, src, dst):
        argv = [self.rsync_command, "-e", self.ssh_command, "-a", src, dst]
        proc = subprocess.run(argv, capture_output=True, text=True)
        if proc.returncode != 0:
            raise StageError(
                f"rsync {src} -> {dst} failed ({proc.returncode}): "
                f"{proc.stderr.strip()}"
            )
