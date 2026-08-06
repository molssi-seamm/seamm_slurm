# -*- coding: utf-8 -*-

"""Run SLURM CLI commands directly on the current host."""

import subprocess

from .backend import SlurmBackend


class LocalSlurm(SlurmBackend):
    """Talks to SLURM's CLI (``sbatch``/``squeue``/``sacct``/``scancel``)
    directly on the current host -- the case where the caller (e.g. a
    JobServer) runs on a SLURM submit host, such as a cluster's head/login
    node, with those commands on ``PATH``."""

    def _run(self, argv, input_text=None):
        proc = subprocess.run(
            argv,
            input=input_text,
            capture_output=True,
            text=True,
        )
        return proc.returncode, proc.stdout, proc.stderr
