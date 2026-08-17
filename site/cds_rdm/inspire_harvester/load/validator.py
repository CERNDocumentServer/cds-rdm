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

from cds_rdm.inspire_harvester.utils import retrieve_identifiers


@dataclass(frozen=True)
class ValidationRule(ABC):
    """Base class for write-time validation rules."""

    @abstractmethod
    def check(self, stream_entry, *, record=None, record_pid=None, matcher=None):
        """Return an error message when the write must not proceed, else ``None``."""
        raise NotImplementedError


@dataclass(frozen=True)
class EpApprovalCreateRule(ValidationRule):
    """Block create when the entry carries an EP approval number."""

    def check(self, stream_entry, *, record=None, record_pid=None, matcher=None):
        """Return an error if ``apprn`` is present on create."""
        apprns = list(
            retrieve_identifiers(
                stream_entry.entry.get("metadata", {}).get("identifiers", []),
                "apprn",
            )
        )
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
        """Return an error if the entry DOI uses the CDS DataCite prefix."""
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
        apprns = list(
            retrieve_identifiers(
                stream_entry.entry.get("metadata", {}).get("identifiers", []),
                "apprn",
            )
        )
        if not apprns:
            return None
        if record.get("access", {}).get("record") != "restricted":
            return None
        return (
            "EP approval number matched a restricted record - record must be "
            "public to be updated by the harvester "
            f"| details: apprn={', '.join(apprns)}, cds_id={record_pid}"
        )


CREATE_RULES = (EpApprovalCreateRule(), CdsDoiCreateRule())
UPDATE_RULES = (EpApprovalUpdateRule(),)


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
