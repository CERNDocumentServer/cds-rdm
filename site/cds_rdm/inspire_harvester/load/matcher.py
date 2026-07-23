# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Record matching module."""

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


@dataclass(frozen=True)
class FilterCandidate:
    """Search filter tried as part of the record-matching priority chain."""

    value: Optional[str]

    @property
    def query(self) -> List[dsl.Q]:
        """Build the search query for this candidate."""
        raise NotImplementedError


@dataclass(frozen=True)
class ParentMatchFilter(FilterCandidate):
    """Match the CDS-RDM parent identifier supplied by INSPIRE."""

    @property
    def query(self):
        """Build the parent identifier query."""
        return [dsl.Q("term", **{"parent.id": self.value})]


@dataclass(frozen=True)
class CDSIdentifierMatchFilter(FilterCandidate):
    """Match a legacy CDS identifier."""

    @property
    def query(self):
        """Build the legacy CDS identifier query."""
        return [
            dsl.Q("term", **{"metadata.identifiers.scheme": "cds"}),
            dsl.Q("term", **{"metadata.identifiers.identifier": self.value}),
        ]


@dataclass(frozen=True)
class DOIMatchFilter(FilterCandidate):
    """Match a DOI."""

    @property
    def query(self):
        """Build the DOI query."""
        return [dsl.Q("term", **{"pids.doi.identifier.keyword": self.value})]


@dataclass(frozen=True)
class InspireIdentifierMatchFilter(FilterCandidate):
    """Match an INSPIRE identifier."""

    @property
    def query(self):
        """Build the INSPIRE identifier query."""
        return [
            dsl.Q("term", **{"metadata.related_identifiers.scheme": "inspire"}),
            dsl.Q(
                "term",
                **{"metadata.related_identifiers.identifier": self.value},
            ),
        ]


@dataclass(frozen=True)
class ArxivIdentifierMatchFilter(FilterCandidate):
    """Match an arXiv identifier."""

    @property
    def query(self):
        """Build the arXiv identifier query."""
        return [
            dsl.Q("term", **{"metadata.related_identifiers.scheme": "arxiv"}),
            dsl.Q(
                "term",
                **{"metadata.related_identifiers.identifier": self.value},
            ),
        ]


@dataclass(frozen=True)
class ReportNumberMatchFilter(FilterCandidate):
    """Match a CDS report number in metadata.identifiers."""

    @property
    def query(self):
        """Build the CDS report number query."""
        return [
            dsl.Q("term", **{"metadata.identifiers.scheme": "cdsrn"}),
            dsl.Q(
                "term",
                **{"metadata.identifiers.identifier": self.value},
            ),
        ]


@dataclass(frozen=True)
class RelatedReportNumberMatchFilter(FilterCandidate):
    """Match a CDS report number in metadata.related_identifiers."""

    @property
    def query(self):
        """Build the related CDS report number query."""
        return [
            dsl.Q("term", **{"metadata.related_identifiers.scheme": "cdsrn"}),
            dsl.Q(
                "term",
                **{"metadata.related_identifiers.identifier": self.value},
            ),
            dsl.Q(
                "term",
                **{"metadata.related_identifiers.relation_type.id": "isvariantformof"},
            ),
        ]


@dataclass(frozen=True)
class ApprovalReportNumberMatchFilter(FilterCandidate):
    """Match an EP/approval report number (apprn) in metadata.identifiers."""

    @property
    def query(self):
        """Build the approval report number query."""
        return [
            dsl.Q("term", **{"metadata.identifiers.scheme": "apprn"}),
            dsl.Q(
                "term",
                **{"metadata.identifiers.identifier": self.value},
            ),
        ]


class RecordMatcher:
    """Finds existing CDS records that match an incoming INSPIRE entry."""

    def match(self, stream_entry, inspire_id, logger) -> MatchResult:
        """Search for existing records using a priority-ordered filter chain."""
        entry = stream_entry.entry
        ctx = entry["_inspire_ctx"]
        filter_candidates = self._build_filter_priority(
            entry, inspire_id, ctx["cds_id"]
        )
        result = None
        for candidate in filter_candidates:
            if candidate.value:
                combined_filter = dsl.Q("bool", filter=candidate.query)
                logger.debug(f"Searching for existing records: {candidate.query}")
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

    def _build_filter_priority(self, entry, inspire_id, cdsrdm_id):
        """Build the priority-ordered record match candidates."""
        doi = entry.get("pids", {}).get("doi", {}).get("identifier")
        identifiers = entry["metadata"].get("identifiers", [])
        related_identifiers = entry["metadata"].get("related_identifiers", [])

        cds_id = self._retrieve_identifier(related_identifiers, "cds")
        arxiv_id = self._retrieve_identifier(related_identifiers, "arxiv")
        report_number = self._retrieve_identifier(identifiers, "cdsrn")
        related_report_number = self._retrieve_identifier(related_identifiers, "cdsrn")
        approval_report_number = self._retrieve_identifier(identifiers, "apprn")
        return [
            ParentMatchFilter(value=cdsrdm_id),
            CDSIdentifierMatchFilter(value=cds_id),
            DOIMatchFilter(value=doi),
            InspireIdentifierMatchFilter(value=inspire_id),
            ArxivIdentifierMatchFilter(value=arxiv_id),
            ReportNumberMatchFilter(value=report_number),
            ApprovalReportNumberMatchFilter(value=approval_report_number),
            RelatedReportNumberMatchFilter(value=related_report_number),
        ]
