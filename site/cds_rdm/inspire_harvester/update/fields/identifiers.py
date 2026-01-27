from typing import List

import copy

from cds_rdm.inspire_harvester.update.engine import Json, UpdateContext, UpdateResult, \
    UpdateConflict
from cds_rdm.inspire_harvester.update.field import FieldUpdateBase
from cds_rdm.inspire_harvester.utils import get_path, set_path


class IdentifiersFieldUpdate(FieldUpdateBase):
    """
    Strategy for list-of-dicts identifiers fields (e.g. metadata.related_identifiers).

    Behaviour:
      1) Recognise existing identifiers by (scheme, identifier) pair.
      2) Append identifiers that are present in incoming but not in current (by pair).
      3) If the *same scheme* exists in both current and incoming but the identifier value
         differs -> CONFLICT (human review).
      4) If current contains identifier schemes that incoming does not contain -> WARNING.

    Notes:
      - This assumes "scheme" is intended to be unique (one identifier per scheme). If you
        legitimately allow multiple identifiers per scheme, you should change the conflict
        rule (e.g. compare by pair only, not by scheme).
      - For an existing (scheme, identifier) pair, we "enrich" the current item with any
        missing keys from incoming (so incoming can add resource_type, etc.) without deleting
        current keys.
    """

    def __init__(self, warn_on_extra_current_schemes: bool = True):
        self.warn_on_extra_current_schemes = warn_on_extra_current_schemes

    def _deep_fill_missing(self, current: dict, incoming: dict) -> dict:
        """Fill missing/empty values in base from incoming, recursively for dicts."""
        out = copy.deepcopy(current)
        for k, v in (incoming or {}).items():
            if k not in out or out[k] in (None, "", [], {}):
                out[k] = copy.deepcopy(v)
            elif isinstance(out[k], dict) and isinstance(v, dict):
                out[k] = self._deep_fill_missing(out[k], v)
        return out

    def update(self, current: Json, incoming: Json, path: str, ctx: UpdateContext) -> UpdateResult:
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
        conflicts =[]
        audit = []

        # Index current by scheme -> (identifier_value, list_index, item)
        # If current already has multiple different identifiers for the same scheme, that's suspicious.
        cur_by_scheme = {}
        cur_pairs = set()

        for idx, item in enumerate(cur_list):
            if not isinstance(item, dict):
                conflicts.append(UpdateConflict(
                    path=path,
                    kind="type_mismatch",
                    message="Identifier entry is not an object",
                    current=item,
                ))
                continue

            scheme = item.get("scheme")
            ident = item.get("identifier")
            if not scheme or not ident:
                conflicts.append(UpdateConflict(
                    path=path,
                    kind="invalid_identifier",
                    message="Identifier entry missing 'scheme' or 'identifier'",
                    current=item,
                ))
                continue

            cur_pairs.add((scheme, ident))
            if scheme in cur_by_scheme and cur_by_scheme[scheme]["identifier"] != ident:
                conflicts.append(UpdateConflict(
                    path=path,
                    kind="duplicate_scheme_in_current",
                    message="Current record has multiple different identifiers for the same scheme",
                    current={"existing": cur_by_scheme[scheme]["item"], "another": item},
                    details={"scheme": scheme},
                ))
            else:
                cur_by_scheme[scheme] = {"identifier": ident, "idx": idx, "item": item}

        inc_schemes = set()
        cur_schemes = set(cur_by_scheme.keys())

        # Process incoming
        for inc_item in inc_list:
            if not isinstance(inc_item, dict):
                conflicts.append(UpdateConflict(
                    path=path,
                    kind="type_mismatch",
                    message="Incoming identifier entry is not an object",
                    incoming=inc_item,
                ))
                continue

            scheme = inc_item.get("scheme")
            ident = inc_item.get("identifier")
            if not scheme or not ident:
                conflicts.append(UpdateConflict(
                    path=path,
                    kind="invalid_identifier",
                    message="Incoming identifier missing 'scheme' or 'identifier'",
                    incoming=inc_item,
                ))
                continue

            inc_schemes.add(scheme)

            # Conflict rule: same scheme but different identifier value
            if scheme in cur_by_scheme and cur_by_scheme[scheme]["identifier"] != ident:
                conflicts.append(UpdateConflict(
                    path=path,
                    kind="scheme_identifier_mismatch",
                    message="Incoming identifier differs for the same scheme",
                    current=cur_by_scheme[scheme]["item"],
                    incoming=inc_item,
                    details={"scheme": scheme,
                             "current_identifier": cur_by_scheme[scheme]["identifier"],
                             "incoming_identifier": ident},
                ))
                continue

            # Pair exists -> enrich existing entry with missing fields from incoming
            if (scheme, ident) in cur_pairs:
                idx = cur_by_scheme[scheme]["idx"]
                updated_list[idx] = self._deep_fill_missing(updated_list[idx], inc_item)
                audit.append(f"{path}: enriched existing identifier ({scheme}, {ident})")
                continue

            # New pair -> append
            updated_list.append(copy.deepcopy(inc_item))
            cur_pairs.add((scheme, ident))
            audit.append(f"{path}: appended identifier ({scheme}, {ident})")

        # Warnings: current has more schemes than incoming
        if self.warn_on_extra_current_schemes:
            extra = sorted(cur_schemes - inc_schemes)
            if extra:
                # If you have a dedicated warnings channel in your system,
                # replace this with `warnings=[...]`. Here we emit audit warnings.
                audit.append(
                    f"WARNING {path}: current has schemes not present in incoming: {extra}"
                )

        updated = copy.deepcopy(current)
        set_path(updated, path, updated_list)
        return UpdateResult(updated=updated, conflicts=conflicts, audit=audit)


class RelatedIdentifiersUpdate(FieldUpdateBase):
    """
    Strategy for InvenioRDM-style `metadata.related_identifiers` (list of dicts).

    Based on the diff screenshot:
      - Incoming may add new related identifiers (green blocks).
      - Current may have extra identifiers that incoming removed (red block).

    Behaviour:
      1) Identify existing entries by (scheme, identifier) pair.
      2) Append any incoming entries whose (scheme, identifier) pair is not present in current.
      3) "Enrich" existing entries with missing fields from incoming (e.g. resource_type),
         without deleting current fields.
      4) WARNING if current has more related identifiers entries than incoming
         (i.e., incoming appears to have removed some).

    Notes:
      - This does *not* delete anything automatically.
      - It does *not* treat "same scheme but different identifier" as conflict, because
        related_identifiers commonly have multiple entries with the same scheme (e.g. many URLs).
        If you want that stricter behaviour, you can add it.
    """

    def __init__(self, warn_if_current_has_more: bool = True):
        self.warn_if_current_has_more = warn_if_current_has_more

    def _pair(self, item: dict) -> tuple:
        return (item.get("scheme"), item.get("identifier"))

    def _deep_fill_missing(self, base: dict, inc: dict) -> dict:
        """Fill missing/empty values in base from inc, recursively for dicts."""
        out = copy.deepcopy(base)
        for k, v in (inc or {}).items():
            if k not in out or out[k] in (None, "", [], {}):
                out[k] = copy.deepcopy(v)
            elif isinstance(out[k], dict) and isinstance(v, dict):
                out[k] = self._deep_fill_missing(out[k], v)
        return out

    def update(self, current: Json, incoming: Json, path: str, ctx: UpdateContext) -> UpdateResult:
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
        conflicts: List[UpdateConflict] = []
        audit: List[str] = []

        # Index current by (scheme, identifier) -> index in list
        # If duplicates exist, we keep the first index and still handle pairs by membership.
        cur_index ={}
        cur_pairs = set()

        for idx, item in enumerate(cur_list):
            if not isinstance(item, dict):
                conflicts.append(UpdateConflict(
                    path=path,
                    kind="type_mismatch",
                    message="Current related_identifier entry is not an object",
                    current=item,
                ))
                continue

            scheme, ident = self._pair(item)
            if not scheme or not ident:
                conflicts.append(UpdateConflict(
                    path=path,
                    kind="invalid_related_identifier",
                    message="Current related_identifier missing 'scheme' or 'identifier'",
                    current=item,
                ))
                continue

            pair = (scheme, ident)
            cur_pairs.add(pair)
            cur_index.setdefault(pair, idx)

        # Apply incoming changes
        for inc_item in inc_list:
            if not isinstance(inc_item, dict):
                conflicts.append(UpdateConflict(
                    path=path,
                    kind="type_mismatch",
                    message="Incoming related_identifier entry is not an object",
                    incoming=inc_item,
                ))
                continue

            scheme, ident = self._pair(inc_item)
            if not scheme or not ident:
                conflicts.append(UpdateConflict(
                    path=path,
                    kind="invalid_related_identifier",
                    message="Incoming related_identifier missing 'scheme' or 'identifier'",
                    incoming=inc_item,
                ))
                continue

            pair = (scheme, ident)

            if pair in cur_pairs:
                # enrich existing entry (e.g. add resource_type)
                idx = cur_index[pair]
                updated_list[idx] = self._deep_fill_missing(updated_list[idx], inc_item)
                audit.append(f"{path}: enriched existing related_identifier {pair}")
            else:
                updated_list.append(copy.deepcopy(inc_item))
                cur_pairs.add(pair)
                cur_index[pair] = len(updated_list) - 1
                audit.append(f"{path}: appended related_identifier {pair}")

        # Warning: current had more entries than incoming (possible removals)
        if self.warn_if_current_has_more and len(cur_list) > len(inc_list):
            audit.append(
                f"WARNING {path}: current has {len(cur_list)} entries, incoming has {len(inc_list)} "
                f"(incoming may have removed {len(cur_list) - len(inc_list)} related_identifiers)"
            )

        updated = copy.deepcopy(current)
        set_path(updated, path, updated_list)
        return UpdateResult(updated=updated, conflicts=conflicts, audit=audit)