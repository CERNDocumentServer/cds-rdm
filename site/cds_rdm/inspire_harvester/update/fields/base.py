# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Generic reusable field update strategies."""

import copy

from cds_rdm.inspire_harvester.update.engine import UpdateConflict, UpdateResult
from cds_rdm.inspire_harvester.update.field import FieldUpdateBase
from cds_rdm.inspire_harvester.utils import get_path, set_path


class OverwriteFieldUpdate(FieldUpdateBase):
    """Prefer the incoming field."""

    def update(self, current, incoming, path, ctx):
        """Replace the current value with the incoming one; no-op if incoming is None."""
        inc_v = get_path(incoming, path)
        if inc_v is None:
            return UpdateResult(updated=current)

        updated = copy.deepcopy(current)
        set_path(updated, path, copy.deepcopy(inc_v))
        return UpdateResult(updated=updated, audit=[f"{path}: overwritten"])


class PreferCurrentMergeDictUpdate(FieldUpdateBase):
    """Merge two dicts, preferring current values over incoming ones.

    Keys listed in ``keep_incoming_keys`` are taken from incoming regardless.
    """

    def __init__(self, keep_incoming_keys):
        """Initialize with the list of keys that incoming values should override."""
        self.keep_incoming_keys = keep_incoming_keys

    def update(self, current, incoming, path, ctx):
        """Merge the dict at ``path``, keeping current values unless incoming has priority."""
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
        """Initialize with the dict key used to identify items and the enrich flag."""
        self.key_field = key_field
        self.enrich_existing = enrich_existing

    def _deep_fill_missing(self, base, inc):
        """Recursively fill empty/missing keys in ``base`` with values from ``inc``."""
        out = copy.deepcopy(base)
        for k, v in (inc or {}).items():
            if k not in out or out[k] in (None, "", [], {}):
                out[k] = copy.deepcopy(v)
            elif isinstance(out[k], dict) and isinstance(v, dict):
                out[k] = self._deep_fill_missing(out[k], v)
        return out

    def update(self, current, incoming, path, ctx):
        """Append unique incoming items to the list at ``path``; optionally enrich existing ones."""
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