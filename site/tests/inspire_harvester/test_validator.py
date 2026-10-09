# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""INSPIRE harvester write-time validator tests."""

from unittest.mock import Mock

from flask import current_app
from invenio_pidstore.models import PersistentIdentifier, PIDStatus

from cds_rdm.inspire_harvester.load.validator import (
    EpApprovalPidstoreRule,
    RecordValidator,
)
from cds_rdm.inspire_harvester.logger import Logger
from cds_rdm.inspire_harvester.transform.context import MetadataSerializationContext
from cds_rdm.inspire_harvester.transform.mappers.identifiers import IdentifiersMapper
from cds_rdm.inspire_harvester.transform.resource_types import ResourceType
from cds_rdm.requests.committee_approval import APPRN_PID_TYPE


def _entry_with_apprn(number):
    return Mock(
        entry={
            "metadata": {
                "identifiers": [{"scheme": "apprn", "identifier": number}],
            }
        }
    )


def test_mapper_stores_ep_report_number_as_apprn(running_app):
    """EP report numbers from INSPIRE are mapped with scheme apprn for the rule."""
    current_app.config["CDS_COMMITTEE_APPROVAL_COMMUNITIES"] = {
        "ep-community": {
            "report_number": {"prefix": "CERN-EP"},
        }
    }
    number = "CERN-EP-2099-001"
    identifiers = IdentifiersMapper().map_value(
        {
            "metadata": {"report_numbers": [{"value": number}]},
            "created": "2023-01-01",
        },
        MetadataSerializationContext(
            resource_type=ResourceType.OTHER, inspire_id="12345"
        ),
        Logger(inspire_id="12345"),
    )
    entry = Mock(entry={"metadata": {"identifiers": identifiers}})

    assert {"identifier": number, "scheme": "apprn"} in identifiers
    msg = EpApprovalPidstoreRule().check(entry)
    assert msg is not None
    assert "not minted in CDS" in msg
    assert number in msg


def test_ep_pidstore_rule_passes_when_apprn_is_minted(running_app, db):
    """EP numbers already minted through CDS are allowed through this rule."""
    number = "CERN-EP-2099-002"
    PersistentIdentifier.create(
        pid_type=APPRN_PID_TYPE,
        pid_value=number,
        object_type="rec",
        object_uuid="00000000-0000-0000-0000-000000000099",
        status=PIDStatus.REGISTERED,
    )
    db.session.commit()

    assert EpApprovalPidstoreRule().check(_entry_with_apprn(number)) is None


def test_validator_blocks_update_for_unminted_apprn(running_app, db):
    """Update path also runs the pidstore check."""
    validator = RecordValidator(matcher=Mock())
    errors = validator.validate(
        "update",
        _entry_with_apprn("CERN-EP-2099-003"),
        record={"access": {"record": "public"}},
        record_pid="abcde-12345",
    )

    assert len(errors) == 1
    assert "not minted in CDS" in errors[0]


def test_validator_blocks_update_of_restricted_record(running_app):
    """A restricted record is never updated."""
    validator = RecordValidator(matcher=Mock())
    errors = validator.validate(
        mode="update",
        stream_entry=Mock(entry={"metadata": {}}),
        record={"access": {"record": "restricted", "files": "public"}},
        record_pid="abcde-fghij",
    )
    assert any("Matched record is restricted" in e for e in errors)


def test_validator_blocks_update_of_record_with_restricted_files(running_app):
    """A record with restricted files is never updated."""
    validator = RecordValidator(matcher=Mock())
    errors = validator.validate(
        mode="update",
        stream_entry=Mock(entry={"metadata": {}}),
        record={"access": {"record": "public", "files": "restricted"}},
        record_pid="abcde-fghij",
    )
    assert any("restricted files" in e for e in errors)


def test_validator_allows_update_of_public_record(running_app):
    """Public records with public files pass the access rules."""
    validator = RecordValidator(matcher=Mock())
    errors = validator.validate(
        mode="update",
        stream_entry=Mock(entry={"metadata": {}}),
        record={"access": {"record": "public", "files": "public"}},
        record_pid="abcde-fghij",
    )
    assert errors == []
