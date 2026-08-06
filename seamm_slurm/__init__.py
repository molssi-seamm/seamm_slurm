# -*- coding: utf-8 -*-

"""seamm_slurm: a SLURM CLI backend (submit/poll/cancel) for SEAMM."""

from .backend import SlurmBackend, SlurmError, SlurmSubmitError  # noqa: F401
from .local import LocalSlurm  # noqa: F401
from .ssh import SshSlurm  # noqa: F401
from .status import JobStatus, classify  # noqa: F401
from ._version import __version__  # noqa: F401
