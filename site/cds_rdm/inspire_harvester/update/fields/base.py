import copy

from cds_rdm.inspire_harvester.update.engine import UpdateResult, UpdateConflict
from cds_rdm.inspire_harvester.update.field import FieldUpdateBase
from cds_rdm.inspire_harvester.utils import get_path, set_path


class OverwriteFieldUpdate(FieldUpdateBase):

    def update(self, current, incoming, path, ctx):
        inc_v = get_path(incoming, path)
        if inc_v is None:
            return UpdateResult(updated=current)

        updated = copy.deepcopy(current)
        set_path(updated, path, copy.deepcopy(inc_v))
        return UpdateResult(updated=updated, audit=[f"{path}: overwritten"])


class PreferCurrentMergeDictUpdate(FieldUpdateBase):

    def __init__(self, keep_incoming_keys):
        self.keep_incoming_keys = keep_incoming_keys

    def update(self, current, incoming, path, ctx):
        cur_v = get_path(current, path)
        inc_v = get_path(incoming, path)

        if inc_v is None:
            return UpdateResult(updated=current)

        if cur_v is None:
            updated = copy.deepcopy(current)
            set_path(updated, path, copy.deepcopy(inc_v))
            return UpdateResult(updated=updated)

        if not isinstance(cur_v, dict) or not isinstance(inc_v, dict):
            return UpdateResult(
                updated=current,
                conflicts=[UpdateConflict(
                    path=path,
                    kind="type_mismatch",
                    message="Expected dicts to merge",
                    current=cur_v,
                    incoming=inc_v,
                )],
            )

        merged = copy.deepcopy(inc_v)
        for k, v in cur_v.items():
            if k in self.keep_incoming_keys:
                continue
            if k not in merged or merged[k] in (None, "", [], {}):
                merged[k] = copy.deepcopy(v)

        updated = copy.deepcopy(current)
        set_path(updated, path, merged)
        return UpdateResult(updated=updated, audit=[f"{path}: merged dict"])


class ListOfDictAppendUniqueUpdate(FieldUpdateBase):
    """
    Append-only merge for a list-of-dicts field.

    - Identifies items by a key extracted from each dict (e.g. item["subject"] or item["id"]).
    - Appends incoming items whose key is not already present in current.
    - Never removes anything.
    - Optionally "enrich" an existing item (same key) by filling missing fields.

    Example:
      current  = [{"subject":"A"}, {"subject":"B"}]
      incoming = [{"subject":"C"}]
      -> [{"subject":"A"}, {"subject":"B"}, {"subject":"C"}]
    """

    def __init__(
        self,
        key_field: str,
        *,
        enrich_existing: bool = False,
    ):
        self.key_field = key_field
        self.enrich_existing = enrich_existing


    def _deep_fill_missing(self, base, inc):
        out = copy.deepcopy(base)
        for k, v in (inc or {}).items():
            if k not in out or out[k] in (None, "", [], {}):
                out[k] = copy.deepcopy(v)
            elif isinstance(out[k], dict) and isinstance(v, dict):
                out[k] = self._deep_fill_missing(out[k], v)
        return out

    def update(self, current, incoming, path, ctx):
        cur_list = get_path(current, path) or []
        inc_list = get_path(incoming, path)

        if inc_list is None:
            return UpdateResult(updated=current)

        if not isinstance(cur_list, list) or not isinstance(inc_list, list):
            return UpdateResult(
                updated=current,
                conflicts=[UpdateConflict(
                    path=path,
                    kind="type_mismatch",
                    message="Expected lists at path",
                    current=cur_list,
                    incoming=inc_list,
                )],
            )

        updated_list = copy.deepcopy(cur_list)
        audit = []
        conflicts = []

        # index current by key
        idx_by_key = {}
        for idx, item in enumerate(cur_list):
            k = item.get(self.key_field)
            # keep first occurrence
            idx_by_key.setdefault(k, idx)

        # process incoming
        for inc_item in inc_list:

            k = inc_item.get(self.key_field)
            if k in idx_by_key:
                if self.enrich_existing:
                    idx = idx_by_key[k]
                    updated_list[idx] = self._deep_fill_missing(updated_list[idx], inc_item)
                    audit.append(f"{path}: enriched item {self.key_field}={k!r}")
                continue

            updated_list.append(copy.deepcopy(inc_item))
            idx_by_key[k] = len(updated_list) - 1
            audit.append(f"{path}: appended item {self.key_field}={k!r}")

        updated = copy.deepcopy(current)
        set_path(updated, path, updated_list)
        return UpdateResult(updated=updated, conflicts=conflicts, audit=audit)