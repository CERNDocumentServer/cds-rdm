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
    current: Any = None
    incoming: Any = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UpdateResult:
    """Holds the result of applying an update strategy to a record."""

    updated: Json
    conflicts: List[UpdateConflict] = field(default_factory=list)
    audit: List[str] = field(default_factory=list)


@dataclass
class UpdateContext:
    """Context passed to each field update strategy."""

    source: Union[str, None]

@dataclass
class UpdateEngine:
    """Applies a set of field update strategies to produce a merged record."""

    strategies: Dict[str, FieldUpdateBase]
    fail_on_conflict: bool = False

    def update(self, current, incoming, ctx):
        """Apply all strategies and return the merged UpdateResult."""
        updated = copy.deepcopy(current)
        conflicts = []
        audit = []

        for path, strategy in self.strategies.items():
            res = strategy.apply(updated, incoming, path, ctx)
            updated = res.updated
            conflicts.extend(res.conflicts)
            audit.extend(res.audit)

        if self.fail_on_conflict and conflicts:
            raise RuntimeError(conflicts)

        return UpdateResult(updated=updated, conflicts=conflicts, audit=audit)
