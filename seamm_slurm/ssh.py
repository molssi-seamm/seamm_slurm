# -*- coding: utf-8 -*-

"""Run SLURM CLI commands on a remote host over SSH."""

import shlex
import subprocess

from .backend import SlurmBackend


class SshSlurm(SlurmBackend):
    """Talks to SLURM's CLI on a remote host over passwordless SSH -- the
    case where the caller (e.g. a JobServer) does not itself run on a SLURM
    submit host, and reaches the cluster's login/head node over SSH instead.

    Assumes key-based, passwordless auth is already set up for ``host``
    (e.g. via an ``~/.ssh/config`` alias), the same way a user would run
    ``ssh <host> sbatch ...`` by hand.
    """

    def __init__(self, host, *, ssh_command="ssh"):
        super().__init__()
        self.host = host
        self.ssh_command = ssh_command

    def _run(self, argv, input_text=None):
        remote_cmd = " ".join(shlex.quote(a) for a in argv)
        proc = subprocess.run(
            [self.ssh_command, self.host, remote_cmd],
            input=input_text,
            capture_output=True,
            text=True,
        )
        return proc.returncode, proc.stdout, proc.stderr
