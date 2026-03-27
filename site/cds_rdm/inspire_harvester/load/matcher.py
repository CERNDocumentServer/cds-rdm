# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Record matching module."""

from collections import OrderedDict
from dataclasses import dataclass, field
from typing import List, Optional

from invenio_access.permissions import system_identity
from invenio_rdm_records.proxies import current_rdm_records_service
from invenio_search.engine import dsl


@dataclass
class MatchResult:
    """Result of a record match attempt."""

    ambiguous: bool = False
    found: bool = False
    record_pid: Optional[str] = None
    matched_ids: List[str] = field(default_factory=list)


class RecordMatcher:
    """Finds existing CDS records that match an incoming INSPIRE entry."""

    def match(self, stream_entry, inspire_id, logger) -> MatchResult:
        """Search for existing records using a priority-ordered filter chain."""
        entry = stream_entry.entry
        ctx = entry["_inspire_ctx"]
        filters_priority = self._build_filter_priority(entry, inspire_id, ctx["cds_id"])
        result = None
        for filter_key, filter_data in filters_priority.items():
            if filter_data["value"]:
                combined_filter = dsl.Q("bool", filter=filter_data["filter"])
                logger.debug(f"Searching for existing records: {filter_data['filter']}")
                result = current_rdm_records_service.search(
                    system_identity, extra_filter=combined_filter
                )
                if result.total >= 1:
                    logger.debug(f"Found {result.total} matching records.")
                    break

        if result is None or result.total == 0:
            return MatchResult(found=False)

        hits = result.to_dict()["hits"]["hits"]
        matched_ids = [hit["id"] for hit in hits]

        if result.total > 1:
            return MatchResult(ambiguous=True, matched_ids=matched_ids)

        return MatchResult(
            found=True, record_pid=matched_ids[0], matched_ids=matched_ids
        )

    def _retrieve_identifier(self, identifiers, scheme) -> Optional[str]:
        """Retrieve identifier by scheme."""
        return next(
            (d["identifier"] for d in identifiers if d["scheme"] == scheme),
            None,
        )

    def _build_filter_priority(self, entry, inspire_id, cdsrdm_id) -> OrderedDict:
        """Build ordered filter dict for priority-based record lookup."""
        doi = entry.get("pids", {}).get("doi", {}).get("identifier")
        related_identifiers = entry["metadata"].get("related_identifiers", [])

        cds_id = self._retrieve_identifier(related_identifiers, "cds")
        arxiv_id = self._retrieve_identifier(related_identifiers, "arxiv")
        report_number = self._retrieve_identifier(related_identifiers, "cdsrn")
        return OrderedDict(
            cds_pid={
                # INSPIRE stores parent PID
                "filter": [dsl.Q("term", **{"parent.id": cdsrdm_id})],
                "value": cdsrdm_id,
            },
            cds_identifiers={
                "filter": [
                    dsl.Q("term", **{"metadata.identifiers.scheme": "cds"}),
                    dsl.Q("term", **{"metadata.identifiers.identifier": cds_id}),
                ],
                "value": cds_id,
            },
            doi={
                "filter": [dsl.Q("term", **{"pids.doi.identifier.keyword": doi})],
                "value": doi,
            },
            inspire_id={
                "filter": [
                    dsl.Q("term", **{"metadata.related_identifiers.scheme": "inspire"}),
                    dsl.Q(
                        "term",
                        **{"metadata.related_identifiers.identifier": inspire_id},
                    ),
                ],
                "value": inspire_id,
            },
            arxiv_filters={
                "filter": [
                    dsl.Q("term", **{"metadata.related_identifiers.scheme": "arxiv"}),
                    dsl.Q(
                        "term",
                        **{"metadata.related_identifiers.identifier": arxiv_id},
                    ),
                ],
                "value": arxiv_id,
            },
            report_number_filters={
                "filter": [
                    dsl.Q("term", **{"metadata.related_identifiers.scheme": "cdsrn"}),
                    dsl.Q(
                        "term",
                        **{"metadata.related_identifiers.identifier": report_number},
                    ),
                ],
                "value": report_number,
            },
        )
