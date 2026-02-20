# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Field update strategy for creators and contributors."""

import copy

from cds_rdm.inspire_harvester.update.engine import UpdateConflict, UpdateResult
from cds_rdm.inspire_harvester.update.field import FieldUpdateBase
from cds_rdm.inspire_harvester.utils import get_path, set_path


class CreatibutorsFieldUpdate(FieldUpdateBase):
    """Merge list-of-dicts of creators/contributors.

    Either merges or emits conflicts for human review.
    """

    def __init__(self, strict=True):
        """Initialize with the strict flag controlling conflict vs. append behaviour."""
        self.strict = strict


    def _union_affiliations(self, cur_list, inc_list):
        """Union by affiliation['name'] (normalized). Keeps full dict objects as present."""
        cur_list = cur_list or []
        inc_list = inc_list or []

        out = []
        seen = set()

        def add(item):
            if not isinstance(item, dict):
                return
            nm = item.get("name")
            if nm and nm in seen:
                return
            out.append(copy.deepcopy(item))
            if nm:
                seen.add(nm)

        for a in cur_list:
            add(a)
        for a in inc_list:
            add(a)

        return out


    def _key(self, creator: dict):
        """Return a hashable key for matching a creator/contributor."""
        p = creator.get("person_or_org") or {}
        ids = p.get("identifiers") or []
        for i in ids:
            if i.get("scheme") and i.get("identifier"):
                return ("id", i["scheme"], i["identifier"])
        return (
            "name",
            (p.get("family_name") or "").lower(),
            (p.get("given_name") or "").lower(),
            (p.get("name") or "").lower(),
        )

    def _merge_creator(self, cur, inc):
        """Merge a single current creator entry with its incoming counterpart."""
        merged = copy.deepcopy(inc)

        # Affiliations: union, never remove
        if "affiliations" in cur or "affiliations" in inc:
            merged["affiliations"] = self._union_affiliations(
                cur.get("affiliations"), inc.get("affiliations")
            )
        # merge person_or_org
        cur_p = cur.get("person_or_org") or {}
        inc_p = inc.get("person_or_org") or {}
        mp = copy.deepcopy(inc_p)

        for k, v in cur_p.items():
            if k == "identifiers":
                continue
            if k not in mp or mp[k] in (None, "", [], {}):
                mp[k] = copy.deepcopy(v)

        # union identifiers
        seen = {(i.get("scheme"), i.get("identifier")) for i in mp.get("identifiers", [])}
        for i in cur_p.get("identifiers", []) or []:
            key = (i.get("scheme"), i.get("identifier"))
            if key not in seen:
                mp.setdefault("identifiers", []).append(copy.deepcopy(i))

        merged["person_or_org"] = mp
        return merged

    def update(self, current, incoming, path, ctx):
        """Match each incoming creator to its current counterpart and merge them."""
        cur_list = get_path(current, path) or []
        inc_list = get_path(incoming, path)

        if inc_list is None:
            return UpdateResult(updated=current)

        updated_list = copy.deepcopy(cur_list)
        conflicts = []
        audit = []

        # index current
        index = {}
        for i, c in enumerate(cur_list):
            index.setdefault(self._key(c), []).append(i)

        for inc in inc_list:
            k = self._key(inc)
            matches = index.get(k, [])

            if not matches:
                if self.strict:
                    conflicts.append(UpdateConflict(
                        path=path,
                        kind="unknown_creator",
                        message="Incoming creator not found",
                        incoming=inc,
                    ))
                else:
                    updated_list.append(copy.deepcopy(inc))
                    audit.append(f"{path}: appended creator {k}")
                continue

            if len(matches) > 1:
                conflicts.append(UpdateConflict(
                    path=path,
                    kind="ambiguous_match",
                    message="Multiple creators match incoming",
                    incoming=inc,
                ))
                continue

            idx = matches[0]
            updated_list[idx] = self._merge_creator(cur_list[idx], inc)
            audit.append(f"{path}: merged creator {k}")

        updated = copy.deepcopy(current)
        set_path(updated, path, updated_list)
        return UpdateResult(updated=updated, conflicts=conflicts, audit=audit)