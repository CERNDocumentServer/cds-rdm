# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Update engine and result data structures for the INSPIRE harvester."""

import copy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Union

from cds_rdm.inspire_harvester.update.field import FieldUpdateBase

Json = Dict[str, Any]


@dataclass
class UpdateConflict:
    """Represents a conflict detected during a field update."""

    path: str
    kind: str
    message: str
    level: str = "error"
    current: Any = None
    incoming: Any = None
    details: Dict[str, Any] = field(default_factory=dict)

    def __str__(self):
        """String representation."""
        return f"{self.path}: {self.current} -> {self.incoming} [{self.kind}] {self.message}"


@dataclass
class UpdateWarning(UpdateConflict):
    """Represents a conflict detected during a field update."""

    level: str = "warning"


@dataclass
class UpdateResult:
    """Holds the result of applying an update strategy to a record."""

    updated: Json
    conflicts: List[UpdateConflict] = field(default_factory=list)
    warnings: List[UpdateConflict] = field(default_factory=list)
    audit: List[str] = field(default_factory=list)


@dataclass
class UpdateContext:
    """Context passed to each field update strategy."""

    source: Union[str, None]


class UpdateEngineConflict(Exception):
    """Update engine conflict exception."""

    def __init__(self, conflicts, *args):
        """Constructor."""
        self.conflicts = conflicts
        super().__init__(*args)


@dataclass
class UpdateEngine:
    """Applies a set of field update strategies to produce a merged record."""

    strategies: Dict[str, FieldUpdateBase]
    fail_on_conflict: bool = False

    def log_conflicts(self, conflicts, logger):
        """Log conflicts in given logger."""
        for conflict in conflicts:
            if conflict.level == "warning":
                logger.warning(str(conflict))
            else:
                logger.error(str(conflict))
            logger.debug(str(conflict.details))

    def update(self, current, incoming, ctx, logger):
        """Apply all strategies and return the merged UpdateResult."""
        updated = copy.deepcopy(current)
        conflicts = []
        warnings = []
        audit = []

        for path, strategy in self.strategies.items():
            res = strategy.apply(updated, incoming, path, ctx)
            updated = res.updated
            conflicts.extend(res.conflicts)
            warnings.extend(res.warnings)
            audit.extend(res.audit)

        if conflicts or warnings:
            self.log_conflicts(conflicts, logger)

        logger.debug(str(audit))

        if self.fail_on_conflict and conflicts:
            raise UpdateEngineConflict(conflicts)

        return UpdateResult(updated=updated, conflicts=conflicts, audit=audit)
