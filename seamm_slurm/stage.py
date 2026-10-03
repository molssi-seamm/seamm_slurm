# -*- coding: utf-8 -*-

"""Compatibility shim: see ``seamm_scheduler.stage``."""

import subprocess  # noqa: F401  (callers patch seamm_slurm.stage.subprocess.run)

from seamm_scheduler.stage import (  # noqa: F401
    STAGE_LOCK_FILENAME,
    JobStager,
    LocalStager,
    RsyncStager,
    StageError,
)
