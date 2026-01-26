from cds_rdm.inspire_harvester.update.field import FieldUpdateBase
from dataclasses import dataclass, field
from typing import Any, Dict, List
import copy

Json = Dict[str, Any]

@dataclass
class UpdateConflict:
    path: str
    kind: str
    message: str
    current: Any = None
    incoming: Any = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UpdateResult:
    updated: Json
    conflicts: List[UpdateConflict] = field(default_factory=list)
    audit: List[str] = field(default_factory=list)


@dataclass
class UpdateContext:
    source: str | None = None

@dataclass
class UpdateEngine:
    strategies: Dict[str, FieldUpdateBase]
    fail_on_conflict: bool = False

    def update(self, current, incoming, ctx):
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