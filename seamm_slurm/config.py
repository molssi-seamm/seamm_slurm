# -*- coding: utf-8 -*-

"""Compatibility shim: see ``seamm_scheduler.config``."""

from seamm_scheduler.config import (  # noqa: F401
    _NON_DIRECTIVE_KEYS,
    _VALID_TYPES,
    FieldLimits,
    SlurmSection,
    TargetSection,
    _parse_size,
    _parse_slurm_value,
    _parse_time,
    list_sections,
    load_slurm_config,
    load_target,
)
