# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Record matching module."""

from dataclasses import dataclass, field
from typing import List, Optional

import requests
from invenio_access.permissions import system_identity
from invenio_rdm_records.proxies import current_rdm_records_service
from invenio_search.engine import dsl
from invenio_vocabularies.datastreams.errors import WriterError
from sqlalchemy.orm.exc import NoResultFound

from cds_rdm.inspire_harvester.utils import retrieve_identifiers
from cds_rdm.legacy.resolver import get_pid_by_legacy_recid
from cds_rdm.schemes import generate_cds_url, legacy_cds_pattern


@dataclass
class MatchResult:
    """Result of a record match attempt."""

    ambiguous: bool = False
    found: bool = False
    unmigrated: bool = False
    record_pid: Optional[str] = None
    matched_ids: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class FilterCandidate:
    """Search filter tried as part of the record-matching priority chain."""

    values: object = None

    def __post_init__(self):
        """Cast ``values`` to a list so callers can pass ids as-is."""
        raw = self.values
        if isinstance(raw, str):
            values = [raw]
        elif raw:
            values = [v for v in raw if v]
        else:
            values = self.values
        object.__setattr__(self, "values", values)

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
        return [dsl.Q("terms", **{"parent.id": self.values})]


@dataclass(frozen=True)
class CDSIdentifierMatchFilter(FilterCandidate):
    """Match a legacy CDS identifier."""

    @property
    def query(self):
        """Build the legacy CDS identifier query."""
        return [
            dsl.Q("term", **{"metadata.identifiers.scheme": "cds"}),
            dsl.Q("terms", **{"metadata.identifiers.identifier": self.values}),
        ]


@dataclass(frozen=True)
class DOIMatchFilter(FilterCandidate):
    """Match a DOI."""

    @property
    def query(self):
        """Build the DOI query."""
        return [dsl.Q("terms", **{"pids.doi.identifier.keyword": self.values})]


@dataclass(frozen=True)
class InspireIdentifierMatchFilter(FilterCandidate):
    """Match an INSPIRE identifier."""

    @property
    def query(self):
        """Build the INSPIRE identifier query."""
        return [
            dsl.Q("term", **{"metadata.related_identifiers.scheme": "inspire"}),
            dsl.Q(
                "terms",
                **{"metadata.related_identifiers.identifier": self.values},
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
                "terms",
                **{"metadata.related_identifiers.identifier": self.values},
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
                "terms",
                **{"metadata.identifiers.identifier": self.values},
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
                "terms",
                **{"metadata.related_identifiers.identifier": self.values},
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
                "terms",
                **{"metadata.identifiers.identifier": self.values},
            ),
        ]


class RecordMatcher:
    """Finds existing CDS records that match an incoming INSPIRE entry."""

    def __init__(self, identity=None):
        """Constructor."""
        self.identity = identity or system_identity

    def match(self, stream_entry, inspire_id, logger) -> MatchResult:
        """Search for existing records using a priority-ordered filter chain."""
        entry = stream_entry.entry
        ctx = entry["_inspire_ctx"]

        migrated = self.match_migrated(entry, logger)
        if migrated.found or migrated.ambiguous or migrated.unmigrated:
            return migrated

        filter_candidates = self._build_filter_priority(
            entry, inspire_id, ctx["cds_id"]
        )
        result = None
        for candidate in filter_candidates:
            if not candidate.values:
                continue
            combined_filter = dsl.Q("bool", filter=candidate.query)
            logger.debug(f"Searching for existing records: {candidate.query}")
            result = current_rdm_records_service.search(
                self.identity, extra_filter=combined_filter
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

    def match_migrated(self, entry, logger):
        """Match a migrated legacy CDS record via ``lrecid`` / old CDS status.

        Returns ``False`` when the entry has no integer legacy CDS identifier.
        """
        identifiers = entry.get("metadata", {}).get("identifiers", [])
        legacy_ids = [
            cds_id
            for cds_id in retrieve_identifiers(identifiers, "cds")
            if legacy_cds_pattern.match(str(cds_id))
        ]
        matched_ids = []
        unresolved = []
        for cds_id in legacy_ids:
            try:
                parent_pid = get_pid_by_legacy_recid(str(cds_id))
                record = current_rdm_records_service.read_latest(
                    self.identity, id_=parent_pid.pid_value
                )
                logger.debug(f"Found record by legacy recid {cds_id}: {record.id}")
                if record.id not in matched_ids:
                    matched_ids.append(record.id)
            except NoResultFound:
                logger.debug(f"No lrecid in pidstore for {cds_id}.")
                unresolved.append(cds_id)

        if matched_ids:
            if len(matched_ids) > 1:
                return MatchResult(ambiguous=True, matched_ids=matched_ids)
            return MatchResult(
                found=True, record_pid=matched_ids[0], matched_ids=matched_ids
            )

        if not unresolved:
            return MatchResult(found=False)

        redirected = []
        still_on_legacy = []
        missing = []
        for cds_id in unresolved:
            response = self._get_legacy_cds(cds_id)
            location = response.headers.get("Location", "")
            status = response.status_code
            if status == 404:
                missing.append(cds_id)
            elif status in (301, 302) and "repository.cern" in location:
                redirected.append(cds_id)
            elif status == 200:
                still_on_legacy.append(cds_id)
            else:
                raise WriterError(
                    "Unexpected response from old CDS. "
                    f"| details: recid={cds_id}, status={status}"
                )

        if redirected:
            raise WriterError(
                "Legacy CDS record redirects to repository.cern but "
                "lrecid is missing from pidstore. "
                f"| details: recid={', '.join(redirected)}"
            )
        if still_on_legacy:
            return MatchResult(unmigrated=True, matched_ids=still_on_legacy)
        raise WriterError(
            "CDS recid from INSPIRE was not found in the old CDS. "
            f"| details: recid={', '.join(missing)}"
        )

    def _get_legacy_cds(self, cds_id):
        """Probe old CDS without following redirects."""
        url = generate_cds_url("cds", str(cds_id))
        return requests.head(url, allow_redirects=False, timeout=60)

    def _build_filter_priority(self, entry, inspire_id, cdsrdm_id):
        """Build the priority-ordered record match candidates."""
        doi = entry.get("pids", {}).get("doi", {}).get("identifier")
        identifiers = entry["metadata"].get("identifiers", [])
        related_identifiers = entry["metadata"].get("related_identifiers", [])

        return [
            ParentMatchFilter(values=cdsrdm_id),
            CDSIdentifierMatchFilter(values=retrieve_identifiers(identifiers, "cds")),
            DOIMatchFilter(values=doi),
            InspireIdentifierMatchFilter(values=inspire_id),
            ArxivIdentifierMatchFilter(
                values=retrieve_identifiers(related_identifiers, "arxiv")
            ),
            ReportNumberMatchFilter(values=retrieve_identifiers(identifiers, "cdsrn")),
            ApprovalReportNumberMatchFilter(
                values=retrieve_identifiers(identifiers, "apprn")
            ),
            RelatedReportNumberMatchFilter(
                values=retrieve_identifiers(related_identifiers, "cdsrn")
            ),
        ]
