# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Record validation module."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from flask import current_app
from invenio_pidstore.models import PersistentIdentifier

from cds_rdm.inspire_harvester.utils import retrieve_identifiers
from cds_rdm.requests.committee_approval import APPRN_PID_TYPE


@dataclass(frozen=True)
class ValidationRule(ABC):
    """Base class for write-time validation rules."""

    @abstractmethod
    def check(self, stream_entry, *, record=None, record_pid=None, matcher=None):
        """Return an error message when the write must not proceed, else ``None``."""
        raise NotImplementedError


def _incoming_apprns(stream_entry):
    """Return EP/approval report numbers from the incoming entry."""
    return list(
        retrieve_identifiers(
            stream_entry.entry.get("metadata", {}).get("identifiers", []),
            "apprn",
        )
    )


@dataclass(frozen=True)
class EpApprovalPidstoreRule(ValidationRule):
    """Block write when an incoming EP number was never minted in CDS.

    CDS is the only place that should mint EP approval numbers. If INSPIRE
    sends one that is not in pidstore, the writer skips create/update for
    that entry and leaves the error on the stream entry for curators.
    """

    def check(self, stream_entry, *, record=None, record_pid=None, matcher=None):
        """Return an error if any incoming ``apprn`` is missing from pidstore."""
        # Collect every apprn from INSPIRE that has no matching PID in CDS.
        # one_or_none() → None means that number was never minted here.
        missing = [
            number
            for number in _incoming_apprns(stream_entry)
            if PersistentIdentifier.query.filter_by(
                pid_type=APPRN_PID_TYPE,
                pid_value=number,
            ).one_or_none()
            is None
        ]
        if not missing:
            return None
        # Non-None return → writer treats this as a failed write and does not
        # create/update the record; the message shows up in the harvest report.
        return (
            "EP approval number is not minted in CDS. "
            "EP approval numbers can only be assigned through the CDS "
            "publishing workflow. "
            f"| details: apprn={', '.join(missing)}"
        )


@dataclass(frozen=True)
class EpApprovalCreateRule(ValidationRule):
    """Block create when the entry carries an EP approval number."""

    def check(self, stream_entry, *, record=None, record_pid=None, matcher=None):
        """Return an error if ``apprn`` is present on create."""
        apprns = _incoming_apprns(stream_entry)
        if not apprns:
            return None
        return (
            "EP approval number did not match an existing record - EP approval "
            "numbers can't be assigned outside CDS publishing workflow. "
            f"| details: apprn={', '.join(apprns)}"
        )


@dataclass(frozen=True)
class CdsDoiCreateRule(ValidationRule):
    """Block create when the entry carries a CDS-minted DOI."""

    def check(self, stream_entry, *, record=None, record_pid=None, matcher=None):
        """Return an error if the entry DOI uses the CDS DataCite prefix.

        On sandbox we allow create with a CDS DOI when the record is missing
        locally (it already exists on prod). Everywhere else, block create so
        we update the existing record instead of minting a duplicate.
        """
        # Same gate as the writer remint path: flag on + sandbox only.
        if (
            current_app.config["CDS_HARVESTER_SANDBOX_ALLOW_CREATE_PROD_MISSING_RECORDS"]
            and current_app.config.get("CDS_ENVIRONMENT_NAME") == "sandbox"
        ):
            return None
        doi = stream_entry.entry.get("pids", {}).get("doi", {})
        prefix = current_app.config["DATACITE_PREFIX"]
        if prefix not in doi.get("identifier", ""):
            return None
        return (
            "Trying to create record with CDS DOI "
            "- record should be updated instead."
        )


@dataclass(frozen=True)
class EpApprovalUpdateRule(ValidationRule):
    """Block update when EP approval matches a restricted record."""

    def check(self, stream_entry, *, record=None, record_pid=None, matcher=None):
        """Return an error if ``apprn`` matches a restricted CDS record."""
        apprns = _incoming_apprns(stream_entry)
        if not apprns:
            return None
        if record.get("access", {}).get("record") != "restricted":
            return None
        return (
            "EP approval number matched a restricted record - record must be "
            "public to be updated by the harvester "
            f"| details: apprn={', '.join(apprns)}, cds_id={record_pid}"
        )


@dataclass(frozen=True)
class RestrictedRecordUpdateRule(ValidationRule):
    """Block update when the matched record is restricted."""

    def check(self, stream_entry, *, record=None, record_pid=None, matcher=None):
        """Return an error if the whole record is restricted."""
        if record.get("access", {}).get("record") != "restricted":
            return None
        return (
            "Matched record is restricted - the harvester does not update "
            f"restricted records. Please verify restrictions. | details: cds_id={record_pid}"
        )


@dataclass(frozen=True)
class RestrictedFilesUpdateRule(ValidationRule):
    """Block update when the matched record has restricted files."""

    def check(self, stream_entry, *, record=None, record_pid=None, matcher=None):
        """Return an error if the record's files are restricted."""
        if record.get("access", {}).get("files") != "restricted":
            return None
        return (
            "Matched record has restricted files - the harvester does not update "
            f"records with restricted files. Please verify restrictions. | details: cds_id={record_pid}"
        )


CREATE_RULES = (EpApprovalPidstoreRule(), EpApprovalCreateRule(), CdsDoiCreateRule())
UPDATE_RULES = (
    EpApprovalPidstoreRule(),
    RestrictedRecordUpdateRule(),
    RestrictedFilesUpdateRule(),
    EpApprovalUpdateRule(),
)


class RecordValidator:
    """Runs mode-specific validation rules before create/update."""

    def __init__(self, matcher):
        """Constructor."""
        self.matcher = matcher
        self.create_rules = CREATE_RULES
        self.update_rules = UPDATE_RULES

    def validate(self, mode, stream_entry, record=None, record_pid=None):
        """Return every failing rule message for the given write mode."""
        rules = {
            "create": self.create_rules,
            "update": self.update_rules,
        }[mode]
        return [
            msg
            for rule in rules
            if (
                msg := rule.check(
                    stream_entry,
                    record=record,
                    record_pid=record_pid,
                    matcher=self.matcher,
                )
            )
        ]
