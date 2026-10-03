# -*- coding: utf-8 -*-

"""seamm_slurm: a SLURM CLI backend (submit/poll/cancel) for SEAMM.

Now a compatibility shim: everything lives in ``seamm_scheduler``, which
generalizes this package to other queueing systems. The names and modules here
are kept so existing importers (``seamm_jobserver``, ``seamm_webui``) keep
working unchanged.
"""

from .backend import SlurmBackend, SlurmError, SlurmSubmitError  # noqa: F401
from .config import (  # noqa: F401
    FieldLimits,
    SlurmSection,
    list_sections,
    load_slurm_config,
)
from .local import LocalSlurm  # noqa: F401
from .ssh import SshSlurm  # noqa: F401
from .stage import JobStager, LocalStager, RsyncStager, StageError  # noqa: F401
from .status import JobStatus, classify  # noqa: F401
from ._version import __version__  # noqa: F401
