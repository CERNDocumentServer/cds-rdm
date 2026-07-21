# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Field update strategy for creators and contributors."""

import copy
import re

from cds_rdm.inspire_harvester.update.engine import UpdateConflict, UpdateResult
from cds_rdm.inspire_harvester.update.field import FieldUpdateBase
from cds_rdm.inspire_harvester.utils import get_path, set_path


def _normalize_affiliation_name(name):
    """Strip punctuation and collapse whitespace for fuzzy name comparison."""
    if not name:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", name)).strip().lower()


class CreatibutorsFieldUpdate(FieldUpdateBase):
    """Merge list-of-dicts of creators/contributors.

    Either merges or emits conflicts for human review.
    """

    def __init__(self, strict=True):
        """Initialize with the strict flag controlling conflict vs. append behaviour."""
        self.strict = strict

    def _union_affiliations(self, cur_list, inc_list):
        """Union affiliations by identifier or name.

        Exact duplicates are skipped. If an incoming affiliation differs from an
        existing one only in punctuation, the existing entry is updated in-place
        with the incoming value rather than adding a second entry.
        """
        cur_list = cur_list or []
        inc_list = inc_list or []

        out = []
        exact_seen = set()
        id_seen = set()
        # Map normalised name → index in out for fuzzy lookup.
        norm_index = {}

        for a in [*cur_list, *inc_list]:
            if not isinstance(a, dict):
                continue
            affiliation_id = a.get("id")
            if affiliation_id:
                if affiliation_id in id_seen:
                    continue
                out.append(copy.deepcopy(a))
                id_seen.add(affiliation_id)
                continue

            nm = a.get("name")
            if not nm:
                out.append(copy.deepcopy(a))
                continue

            if nm in exact_seen:
                # Exact match — already present, skip.
                continue

            norm = _normalize_affiliation_name(nm)
            if norm in norm_index:
                # Punctuation-only difference — update existing entry in-place.
                out[norm_index[norm]] = copy.deepcopy(a)
                exact_seen.add(nm)
            else:
                out.append(copy.deepcopy(a))
                exact_seen.add(nm)
                norm_index[norm] = len(out) - 1

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

    def _have_conflicting_values(self, first, second, ignored=()):
        """Check whether two entries disagree on any meaningful value."""
        empty = (None, "", [], {})
        for key in first:
            first_value, second_value = first.get(key), second.get(key)
            if key in ignored:
                continue
            if first_value in empty or second_value in empty:
                continue
            if first_value != second_value:
                return True
        return False

    def _duplicates_are_compatible(self, creators):
        """Check that every matching creator can be safely merged into one."""
        for i, first in enumerate(creators):
            for second in creators[i + 1 :]:
                if self._have_conflicting_values(
                    first, second, ignored=("affiliations", "person_or_org")
                ):
                    return False
                if self._have_conflicting_values(
                    first.get("person_or_org") or {},
                    second.get("person_or_org") or {},
                    ignored=("identifiers",),
                ):
                    return False
        return True

    def _merge_creator(self, cur, inc):
        """Merge a single current creator entry with its incoming counterpart."""
        merged = copy.deepcopy(inc)

        for key, value in cur.items():
            if key in ("affiliations", "person_or_org"):
                continue
            if key not in merged or merged[key] in (None, "", [], {}):
                merged[key] = copy.deepcopy(value)

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
        seen = {
            (i.get("scheme"), i.get("identifier")) for i in mp.get("identifiers", [])
        }
        for i in cur_p.get("identifiers", []) or []:
            key = (i.get("scheme"), i.get("identifier"))
            if key not in seen:
                mp.setdefault("identifiers", []).append(copy.deepcopy(i))
                seen.add(key)

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
        warnings = []
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
                    warnings.append(
                        UpdateConflict(
                            path=path,
                            kind="new_creator",
                            message="New creator",
                            incoming=inc,
                            level="warning",
                        )
                    )
                else:
                    updated_list.append(copy.deepcopy(inc))
                    index.setdefault(k, []).append(len(updated_list) - 1)
                    audit.append(f"{path}: appended creator {k}")
                continue

            if len(matches) > 1:
                matched_creators = [updated_list[i] for i in matches]
                if not self._duplicates_are_compatible(matched_creators):
                    conflicts.append(
                        UpdateConflict(
                            path=path,
                            kind="ambiguous_match",
                            message="Multiple creators match incoming",
                            incoming=inc,
                        )
                    )
                    continue

                idx = matches[0]
                merged = updated_list[idx]
                for duplicate_idx in matches[1:]:
                    merged = self._merge_creator(
                        merged, updated_list[duplicate_idx]
                    )
                updated_list[idx] = self._merge_creator(merged, inc)

                for duplicate_idx in matches[1:]:
                    updated_list[duplicate_idx] = None
                index[k] = [idx]
                audit.append(
                    f"{path}: merged {len(matches)} duplicate creators {k}"
                )
                continue

            idx = matches[0]
            updated_list[idx] = self._merge_creator(updated_list[idx], inc)
            audit.append(f"{path}: merged creator {k}")

        updated = copy.deepcopy(current)
        set_path(updated, path, [item for item in updated_list if item is not None])
        return UpdateResult(
            updated=updated, conflicts=conflicts, warnings=warnings, audit=audit
        )
