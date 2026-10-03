# -*- coding: utf-8 -*-

"""Compatibility shim: see ``seamm_scheduler.slurm``."""

import subprocess  # noqa: F401  (callers patch seamm_slurm.local.subprocess.run)

from seamm_scheduler.slurm import LocalSlurm  # noqa: F401
