import copy

from cds_rdm.inspire_harvester.update.engine import UpdateResult, UpdateConflict
from cds_rdm.inspire_harvester.update.field import FieldUpdateBase
from cds_rdm.inspire_harvester.utils import get_path, set_path


class ThesisFieldUpdate(FieldUpdateBase):
    """
    Strategy for `metadata.thesis:thesis` (InvenioRDM custom field style).

    Requirements:
      - Allow updating `university` and `type` from incoming.
      - Leave any keys that are missing in incoming intact on the current record
        (e.g. keep current `date_defended`, `date_submitted` if incoming doesn't provide them).
      - Do not delete keys.
      - If incoming thesis object is missing entirely -> no-op.

    Notes:
      - If current thesis object is missing and incoming exists -> set it (full copy).
      - If either side isn't a dict -> conflict.
    """

    def __init__(self, updatable_keys = ("university", "type")):
        self.updatable_keys = updatable_keys

    def update(self, current, incoming, path, ctx):
        cur_obj = get_path(current, path)
        inc_obj = get_path(incoming, path)

        # No incoming thesis data -> nothing to do
        if inc_obj is None:
            return UpdateResult(updated=current)

        # If no current thesis -> set from incoming (safe default)
        if cur_obj is None:
            if not isinstance(inc_obj, dict):
                return UpdateResult(
                    updated=current,
                    conflicts=[UpdateConflict(
                        path=path,
                        kind="type_mismatch",
                        message="Incoming thesis field is not an object",
                        incoming=inc_obj,
                    )],
                )
            updated = copy.deepcopy(current)
            set_path(updated, path, copy.deepcopy(inc_obj))
            return UpdateResult(updated=updated, audit=[f"{path}: set (was missing)"])

        # Both must be dicts to merge
        if not isinstance(cur_obj, dict) or not isinstance(inc_obj, dict):
            return UpdateResult(
                updated=current,
                conflicts=[UpdateConflict(
                    path=path,
                    kind="type_mismatch",
                    message="Expected thesis field to be an object in both current and incoming",
                    current=cur_obj,
                    incoming=inc_obj,
                )],
            )

        merged = copy.deepcopy(cur_obj)

        # Only overwrite explicitly allowed keys IF they exist in incoming.
        for k in self.updatable_keys:
            if k in inc_obj and inc_obj[k] not in (None, "", [], {}):
                merged[k] = copy.deepcopy(inc_obj[k])

        # Keep all other current keys as-is (including date_defended/date_submitted)
        updated = copy.deepcopy(current)
        set_path(updated, path, merged)

        changed_keys = [k for k in self.updatable_keys if k in inc_obj]
        audit = [f"{path}: updated keys {changed_keys} (missing keys preserved)"] if changed_keys else []

        return UpdateResult(updated=updated, audit=audit)