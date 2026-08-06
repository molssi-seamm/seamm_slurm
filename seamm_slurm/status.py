# -*- coding: utf-8 -*-

"""Classification of SLURM job states into a small, stable vocabulary.

Deliberately independent of SEAMM's own job-status vocabulary
(``submitted``/``running``/``finished``/... in ``seamm_jobserver``'s
datastore) -- mapping SLURM states to SEAMM's is the caller's job, not this
library's, so this stays reusable outside SEAMM's specific datastore.
"""

from dataclasses import dataclass, field
from typing import Optional

# SLURM job states, classified into the categories this library exposes.
# Not exhaustive of every SLURM release's state list, but covers the states
# relevant to whether/how a job should be treated as done.
_PENDING_STATES = {
    "PENDING",
    "CONFIGURING",
    "REQUEUE_HOLD",
    "REQUEUED",
    "RESIZING",
    "RESV_DEL_HOLD",
}
_RUNNING_STATES = {
    "RUNNING",
    "COMPLETING",
    "SUSPENDED",
    "STAGE_OUT",
    "SIGNALING",
    "STOPPED",
}
_COMPLETED_STATES = {"COMPLETED"}
_CANCELLED_STATES = {"CANCELLED"}
_FAILED_STATES = {
    "FAILED",
    "TIMEOUT",
    "NODE_FAIL",
    "OUT_OF_MEMORY",
    "BOOT_FAIL",
    "DEADLINE",
    "PREEMPTED",
    "REVOKED",
    "SPECIAL_EXIT",
}


def classify(raw_state):
    """Classify a raw SLURM state string into one of this library's
    categories.

    Parameters
    ----------
    raw_state : str
        A SLURM job state, e.g. ``"RUNNING"``, ``"COMPLETED"``, or (as
        ``sacct`` sometimes reports for a cancelled job) ``"CANCELLED by
        1234"``.

    Returns
    -------
    str
        One of ``"pending"``, ``"running"``, ``"completed"``,
        ``"cancelled"``, ``"failed"``, or ``"unknown"``.
    """
    state = raw_state.split()[0].upper() if raw_state else ""
    if state in _PENDING_STATES:
        return "pending"
    if state in _RUNNING_STATES:
        return "running"
    if state in _COMPLETED_STATES:
        return "completed"
    if state in _CANCELLED_STATES:
        return "cancelled"
    if state in _FAILED_STATES:
        return "failed"
    return "unknown"


_TERMINAL_CATEGORIES = {"completed", "cancelled", "failed"}


@dataclass
class JobStatus:
    """The status of one SLURM job, as last polled."""

    job_id: str
    state: str
    category: str
    exit_code: Optional[str] = None
    reason: Optional[str] = None
    raw: dict = field(default_factory=dict)

    @property
    def is_terminal(self):
        """Whether this job has finished (successfully or not) and is no
        longer pending or running."""
        return self.category in _TERMINAL_CATEGORIES
