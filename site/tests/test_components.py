# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the GPL-2.0 License; see LICENSE file for more details.
"""Test components."""

from copy import deepcopy

import pytest
from flask import current_app
from invenio_access.permissions import system_identity
from invenio_pidstore.errors import PIDAlreadyExists
from invenio_pidstore.models import PersistentIdentifier
from invenio_rdm_records.proxies import current_rdm_records
from invenio_rdm_records.records import RDMRecord
from marshmallow import ValidationError

from cds_rdm.components import (
    MintAlternateIdentifierComponent,
    SubjectsValidationComponent,
)


def test_subjects_validation_component_update_draft(
    minimal_restricted_record, uploader, client
):
    """Test the metadata component."""
    client = uploader.login(client)
    service = current_rdm_records.records_service
    # create draft
    draft = service.create(uploader.identity, minimal_restricted_record)._record

    component = SubjectsValidationComponent(current_rdm_records.records_service)

    new_data = deepcopy(minimal_restricted_record)
    new_data["metadata"]["subjects"] = [
        {"subject": "collection:1234567890"},
        {"subject": "collection:0987654321"},
    ]
    with pytest.raises(ValidationError):
        component.update_draft(uploader.identity, data=new_data, record=draft)

    draft.metadata["subjects"] = [
        {"subject": "collection:1234567890"},
        {"subject": "collection:0987654321"},
    ]
    new_data = deepcopy(minimal_restricted_record)
    new_data["metadata"]["subjects"] = []
    with pytest.raises(ValidationError):
        component.update_draft(uploader.identity, data=new_data, record=draft)


def test_subjects_validation_component_update_draft_admin(
    minimal_restricted_record, uploader, client, administrator
):
    """Test the metadata component."""
    client = uploader.login(client)
    service = current_rdm_records.records_service
    # create draft
    draft = service.create(uploader.identity, minimal_restricted_record)._record

    component = SubjectsValidationComponent(current_rdm_records.records_service)

    new_data = deepcopy(minimal_restricted_record)
    new_data["metadata"]["subjects"] = [
        {"subject": "collection:1234567890"},
        {"subject": "collection:0987654321"},
    ]

    assert (
        component.update_draft(administrator.identity, data=new_data, record=draft)
        == None
    )

    draft.metadata["subjects"] = [
        {"subject": "collection:1234567890"},
        {"subject": "collection:0987654321"},
    ]
    new_data = deepcopy(minimal_restricted_record)
    new_data["metadata"]["subjects"] = []
    assert (
        component.update_draft(administrator.identity, data=new_data, record=draft)
        == None
    )


def test_mint_alternate_identifier_component(
    minimal_restricted_record, uploader, client, administrator, monkeypatch
):
    """Test for the mint alternative identifier component.

    Tests all scenarios:
    1. Normal case - single identifier
    2. Update draft validation
    3. Same scheme, different values
    4. Same value, different schemes
    5. Mixed mintable and non-mintable schemes
    6. PID lifecycle management (deletion, creation, updates)
    7. Duplicate validation
    8. Mixed mintable(with validation errors) and non-mintable schemes
    """

    client = uploader.login(client)
    service = current_rdm_records.records_service
    component = MintAlternateIdentifierComponent(current_rdm_records.records_service)

    monkeypatch.setitem(
        current_app.config,
        "CDS_CERN_MINT_ALTERNATE_IDS",
        {
            "cdsrn": "CDS Reference",
            "testrn": "Test Reference",
        },
    )

    # 1. Normal case - single identifier
    draft1 = service.create(uploader.identity, minimal_restricted_record)._record
    new_data = deepcopy(minimal_restricted_record)
    new_data["metadata"]["identifiers"] = [
        {"scheme": "cdsrn", "identifier": "1234567890"},
    ]
    errors = []
    assert (
        component.update_draft(
            administrator.identity, data=new_data, record=draft1, errors=errors
        )
        == None
    )
    assert len(errors) == 0
    # Publish the draft to create a record
    record1 = RDMRecord.publish(draft1)
    assert (
        component.publish(administrator.identity, draft=draft1, record=record1) == None
    )

    # Verify PID was created
    pids = PersistentIdentifier.query.filter(
        PersistentIdentifier.object_uuid == record1.pid.object_uuid,
        PersistentIdentifier.pid_type == "cdsrn",
        PersistentIdentifier.pid_value == "1234567890",
    ).all()
    assert len(pids) == 1
    assert pids[0].status.value == "R"

    # 2. Test update_draft method with duplicate identifier
    draft2 = service.create(uploader.identity, minimal_restricted_record)._record
    new_data = deepcopy(minimal_restricted_record)
    new_data["metadata"]["identifiers"] = [
        {"scheme": "cdsrn", "identifier": "1234567890"},  # Duplicate
    ]
    errors = []
    component.update_draft(
        administrator.identity, data=new_data, record=draft2, errors=errors
    )
    assert len(errors) > 0
    assert "already exists" in errors[0]["messages"][0]

    # 2. Test update_draft with valid new identifier
    draft3 = service.create(uploader.identity, minimal_restricted_record)._record
    new_data = deepcopy(minimal_restricted_record)
    new_data["metadata"]["identifiers"] = [
        {"scheme": "cdsrn", "identifier": "1234567901"},  # New unique identifier
    ]
    errors = []
    component.update_draft(
        administrator.identity, data=new_data, record=draft3, errors=errors
    )
    assert len(errors) == 0

    # 3. Same scheme, different values
    draft4 = service.create(uploader.identity, minimal_restricted_record)._record
    draft4.metadata["identifiers"] = [
        {"scheme": "cdsrn", "identifier": "1234567891"},
        {"scheme": "cdsrn", "identifier": "1234567892"},
    ]
    record4 = RDMRecord.publish(draft4)
    assert (
        component.publish(administrator.identity, draft=draft4, record=record4) == None
    )

    # Verify both PIDs were created
    pids = PersistentIdentifier.query.filter(
        PersistentIdentifier.object_uuid == record4.pid.object_uuid,
        PersistentIdentifier.pid_type == "cdsrn",
    ).all()
    assert len(pids) == 2
    pid_values = {pid.pid_value for pid in pids}
    assert pid_values == {"1234567891", "1234567892"}

    # 4. Same value, different schemes
    draft5 = service.create(uploader.identity, minimal_restricted_record)._record
    draft5.metadata["identifiers"] = [
        {"scheme": "cdsrn", "identifier": "1234567893"},
        {"scheme": "testrn", "identifier": "1234567893"},
    ]
    record5 = RDMRecord.publish(draft5)
    assert (
        component.publish(administrator.identity, draft=draft5, record=record5) == None
    )

    # Verify PIDs were created for both schemes
    pids = PersistentIdentifier.query.filter(
        PersistentIdentifier.object_uuid == record5.pid.object_uuid,
        PersistentIdentifier.pid_type != record5.pid.pid_type,
    ).all()
    assert len(pids) == 2
    pid_types = {pid.pid_type for pid in pids}
    assert pid_types == {"cdsrn", "testrn"}

    # 5. Mixed mintable and non-mintable schemes
    draft6 = service.create(uploader.identity, minimal_restricted_record)._record
    draft6.metadata["identifiers"] = [
        {"scheme": "cdsrn", "identifier": "1234567894"},  # mintable
        {"scheme": "doi", "identifier": "10.1016/j.epsl.2011.11.037"},  # non-mintable
        {"scheme": "arxiv", "identifier": "arXiv:1310.2590"},  # non-mintable
    ]
    record6 = RDMRecord.publish(draft6)
    assert (
        component.publish(administrator.identity, draft=draft6, record=record6) == None
    )

    # Verify only mintable scheme got PID created
    pids = PersistentIdentifier.query.filter(
        PersistentIdentifier.object_uuid == record6.pid.object_uuid,
        PersistentIdentifier.pid_type != record6.pid.pid_type,
    ).all()
    assert len(pids) == 1
    assert pids[0].pid_type == "cdsrn"
    assert pids[0].pid_value == "1234567894"

    # 6. Create a record with multiple identifiers
    draft7 = service.create(uploader.identity, minimal_restricted_record)._record
    draft7.metadata["identifiers"] = [
        {"scheme": "cdsrn", "identifier": "1234567895"},
        {"scheme": "testrn", "identifier": "1234567896"},
    ]
    record7 = RDMRecord.publish(draft7)
    assert (
        component.publish(administrator.identity, draft=draft7, record=record7) == None
    )

    # Verify both PIDs were created
    pids_before = PersistentIdentifier.query.filter(
        PersistentIdentifier.object_uuid == record7.pid.object_uuid,
        PersistentIdentifier.pid_type != record7.pid.pid_type,
    ).all()
    assert len(pids_before) == 2
    pid_types_before = {pid.pid_type for pid in pids_before}
    assert pid_types_before == {"cdsrn", "testrn"}

    # 6. Test PID deletion: Remove one identifier and republish
    draft7.metadata["identifiers"] = [
        {"scheme": "cdsrn", "identifier": "1234567895"},  # Keep this one
        # Remove testrn identifier
    ]
    assert (
        component.publish(administrator.identity, draft=draft7, record=record7) == None
    )

    # Verify only one PID remains (deletion worked)
    pids_after_deletion = PersistentIdentifier.query.filter(
        PersistentIdentifier.object_uuid == record7.pid.object_uuid,
        PersistentIdentifier.pid_type != record7.pid.pid_type,
    ).all()
    assert len(pids_after_deletion) == 1
    assert pids_after_deletion[0].pid_type == "cdsrn"
    assert pids_after_deletion[0].pid_value == "1234567895"

    # 6. Test PID creation: Add a new identifier
    draft7.metadata["identifiers"] = [
        {"scheme": "cdsrn", "identifier": "1234567895"},  # Keep existing
        {"scheme": "testrn", "identifier": "1234567897"},  # Add new
    ]
    assert (
        component.publish(administrator.identity, draft=draft7, record=record7) == None
    )

    # Verify two PIDs exist now (creation worked)
    pids_after_creation = PersistentIdentifier.query.filter(
        PersistentIdentifier.object_uuid == record7.pid.object_uuid,
        PersistentIdentifier.pid_type != record7.pid.pid_type,
    ).all()
    assert len(pids_after_creation) == 2
    pid_types_after_creation = {pid.pid_type for pid in pids_after_creation}
    assert pid_types_after_creation == {"cdsrn", "testrn"}

    # 6. Test PID updates: Change an identifier value
    draft7.metadata["identifiers"] = [
        {"scheme": "cdsrn", "identifier": "1234567898"},  # Changed value
        {"scheme": "testrn", "identifier": "1234567897"},  # Keep this one
    ]
    assert (
        component.publish(administrator.identity, draft=draft7, record=record7) == None
    )

    # Verify old PID was deleted and new one was created (update worked)
    pids_after_update = PersistentIdentifier.query.filter(
        PersistentIdentifier.object_uuid == record7.pid.object_uuid,
        PersistentIdentifier.pid_type != record7.pid.pid_type,
    ).all()
    assert len(pids_after_update) == 2
    assert {pid.pid_value for pid in pids_after_update} == {"1234567898", "1234567897"}

    # Verify old PID no longer exists
    old_pids = PersistentIdentifier.query.filter(
        PersistentIdentifier.pid_type == "cdsrn",
        PersistentIdentifier.pid_value == "1234567895",
    ).all()
    assert len(old_pids) == 0

    # 7. Duplicate validation
    draft9 = service.create(uploader.identity, minimal_restricted_record)
    draft9._record.metadata["identifiers"] = [
        {
            "scheme": "cdsrn",
            "identifier": "1234567890",
        },  # This already exists from draft1
    ]

    errors = []
    component.update_draft(
        administrator.identity, data=draft9.data, record=draft9._record, errors=errors
    )
    assert len(errors) > 0
    # This should raise PIDAlreadyExists error
    record9 = RDMRecord.publish(draft9._record)
    with pytest.raises(PIDAlreadyExists):
        component.publish(administrator.identity, draft=draft9._record, record=record9)

    # 8. Mintable(with validation errors) and non-mintable schemes
    draft10 = service.create(uploader.identity, minimal_restricted_record)
    draft10._record.metadata["identifiers"] = [
        {"scheme": "cdsrn", "identifier": "1234567890"},  # Already exists from draft1
        {"scheme": "arxiv", "identifier": "arXiv:1310.2590"},
    ]
    draft10 = service.update_draft(system_identity, draft10.id, data=draft10.data)

    # Check if non-mintable scheme is saved in draft
    assert draft10.data["metadata"]["identifiers"] == [
        {"scheme": "cdsrn", "identifier": "1234567890"},
        {"scheme": "arxiv", "identifier": "arXiv:1310.2590"},
    ]
