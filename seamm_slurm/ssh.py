# -*- coding: utf-8 -*-

"""Compatibility shim: see ``seamm_scheduler.slurm``."""

import subprocess  # noqa: F401  (callers patch seamm_slurm.ssh.subprocess.run)

from seamm_scheduler.slurm import SshSlurm  # noqa: F401
