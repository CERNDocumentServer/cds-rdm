# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""INSPIRE to CDS harvester module."""

from dataclasses import dataclass

from invenio_access.permissions import system_identity
from invenio_records_resources.proxies import current_service_registry

from cds_rdm.inspire_harvester.transform.mappers.mapper import MapperBase


def _normalize(value):
    """Normalize free-text for comparison."""
    return (value or "").strip().lower()


def _funder_matches(hit, agency):
    """Return True if a funder hit matches the INSPIRE agency string."""
    needle = _normalize(agency)
    if not needle:
        return False
    if _normalize(hit.get("name")) == needle:
        return True
    title = hit.get("title") or {}
    return any(_normalize(v) == needle for v in title.values())


@dataclass(frozen=True)
class FundingMapper(MapperBase):
    """Mapper for funding information."""

    id = "metadata.funding"

    def _resolve_funder(self, agency, ctx, logger):
        """Resolve a funder vocabulary id from an agency name, or None."""
        if not agency:
            return None

        try:
            service = current_service_registry.get("funders")
            result = service.search(system_identity, q=agency, size=20)
            matches = [h for h in result.hits if _funder_matches(h, agency)]
            if len(matches) == 1:
                return matches[0]["id"]
            if not matches and result.total == 1:
                return list(result.hits)[0]["id"]
            return None
        except Exception as e:
            logger.error(
                f"Failed funder search. "
                f"| details: agency={agency}, error={e}"
            )
            return None

    def _resolve_award(self, number, funder_id, ctx, logger):
        """Resolve an award vocabulary id from a grant/project number, or None."""
        if not number:
            return None, None

        try:
            service = current_service_registry.get("awards")
            query = f'number:"{number}"'
            if funder_id:
                query = f"{query} AND funder.id:{funder_id}"
            result = service.search(system_identity, q=query, size=20)
            hits = list(result.hits)

            if funder_id and not hits:
                # Fall back to number-only search if funder-scoped search missed.
                result = service.search(
                    system_identity, q=f'number:"{number}"', size=20
                )
                hits = list(result.hits)

            exact = [h for h in hits if str(h.get("number")) == str(number)]
            candidates = exact or hits
            if len(candidates) == 1:
                return candidates[0]["id"], candidates[0]
            return None, None
        except Exception as e:
            logger.error(
                f"Failed award search. "
                f"| details: grant_number={number}, error={e}"
            )
            return None, None

    def map_value(self, src_record, ctx, logger):
        """Map funding_info entries to funder/award vocabulary references.

        Requires vocabulary ids. Missing funder or award ids are reported as
        curator errors (no free-text fallback).
        """
        src_metadata = src_record.get("metadata", {})
        funding_info = src_metadata.get("funding_info", [])
        if not funding_info:
            return None

        mapped = []
        for entry in funding_info:
            agency = entry.get("agency")
            grant_number = entry.get("grant_number") or entry.get("project_number")

            funder_id = self._resolve_funder(agency, ctx, logger) if agency else None
            award_id = None
            award_hit = None
            if grant_number:
                award_id, award_hit = self._resolve_award(
                    grant_number, funder_id, ctx, logger
                )

            # Award can provide the funder when agency was missing/unresolved.
            if not funder_id and award_hit:
                funder = award_hit.get("funder") or {}
                funder_id = funder.get("id")

            if agency and not funder_id:
                ctx.errors.append(
                    "Funder not found in vocabulary. "
                    f"| details: agency={agency}"
                )
                continue

            if grant_number and not award_id:
                ctx.errors.append(
                    "Award not found in vocabulary. "
                    f"| details: grant_number={grant_number}, agency={agency}"
                )
                continue

            if not funder_id:
                ctx.errors.append(
                    "Funding entry missing resolvable funder id. "
                    f"| details: entry={entry}"
                )
                continue

            funding = {"funder": {"id": funder_id}}
            if award_id:
                funding["award"] = {"id": award_id}
            mapped.append(funding)

        return mapped or None
