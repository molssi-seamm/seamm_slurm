# -*- coding: utf-8 -*-

"""Compatibility shim: see ``seamm_scheduler.slurm``."""

from seamm_scheduler.slurm import (  # noqa: F401
    SlurmBackend,
    SlurmError,
    SlurmSubmitError,
)
