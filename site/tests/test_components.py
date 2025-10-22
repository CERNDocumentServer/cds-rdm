# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the GPL-2.0 License; see LICENSE file for more details.
"""Test components."""

from copy import deepcopy
from tkinter import N

import pytest
from flask import current_app
from invenio_pidstore.models import PersistentIdentifier, PIDStatus
from invenio_rdm_records.proxies import current_rdm_records
from invenio_rdm_records.services.components import DefaultRecordsComponents
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
    minimal_restricted_record, uploader, client, monkeypatch
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

    monkeypatch.setitem(
        current_app.config,
        "RDM_RECORDS_IDENTIFIERS_SCHEMES",
        {
            **current_app.config["RDM_RECORDS_IDENTIFIERS_SCHEMES"],
            "cdsrn": {
                "label": "CDS Reference",
                "validator": lambda x: True,
                "datacite": "CDS",
            },
            "testrn": {
                "label": "Test Reference",
                "validator": lambda x: True,
                "datacite": "Test",
            },
        },
    )
    monkeypatch.setitem(
        current_app.config,
        "CDS_CERN_MINT_ALTERNATE_IDS",
        {
            "cdsrn": "CDS Reference",
            "testrn": "Test Reference",
        },
    )
    monkeypatch.setitem(
        current_app.config,
        "RDM_RECORDS_SERVICE_COMPONENTS",
        [*DefaultRecordsComponents, MintAlternateIdentifierComponent],
    )

    # 1. Normal case - single identifier
    new_data = deepcopy(minimal_restricted_record)
    new_data["metadata"]["identifiers"] = [
        {"scheme": "cdsrn", "identifier": "1234567890"},
    ]
    draft1 = service.create(uploader.identity, new_data)
    assert len(draft1.errors) == 0
    # Publish the draft to create a record
    record1 = service.publish(uploader.identity, id_=draft1.id)._record

    # Verify PID was created
    pids = PersistentIdentifier.query.filter(
        PersistentIdentifier.object_uuid == record1.pid.object_uuid,
        PersistentIdentifier.pid_type == "cdsrn",
        PersistentIdentifier.pid_value == "1234567890",
    ).all()
    assert len(pids) == 1
    assert pids[0].status == PIDStatus.REGISTERED

    # 2. Test update_draft method with duplicate identifier
    draft2 = service.create(uploader.identity, new_data)
    # Re-use the same draft data to test the duplicate validation
    assert len(draft2.errors) > 0
    assert "already exists" in draft2.errors[0]["messages"][0]

    # 2. Test update_draft with valid new identifier
    draft3 = service.create(uploader.identity, minimal_restricted_record)
    draft3.data["metadata"]["identifiers"] = [
        {"scheme": "cdsrn", "identifier": "1234567901"},  # New unique identifier
    ]
    draft3 = service.update_draft(uploader.identity, id_=draft3.id, data=draft3.data)
    assert len(draft3.errors) == 0

    # 3. Same scheme, different values
    new_data["metadata"]["identifiers"] = [
        {"scheme": "cdsrn", "identifier": "1234567891"},
        {"scheme": "cdsrn", "identifier": "1234567892"},
    ]
    draft4 = service.create(uploader.identity, new_data)

    record4 = service.publish(uploader.identity, id_=draft4.id)._record
    # Verify both PIDs were created
    pids = PersistentIdentifier.query.filter(
        PersistentIdentifier.object_uuid == record4.pid.object_uuid,
        PersistentIdentifier.pid_type == "cdsrn",
    ).all()
    assert len(pids) == 2
    pid_values = {pid.pid_value for pid in pids}
    assert pid_values == {"1234567891", "1234567892"}

    # 4. Same value, different schemes
    new_data["metadata"]["identifiers"] = [
        {"scheme": "cdsrn", "identifier": "1234567893"},
        {"scheme": "testrn", "identifier": "1234567893"},
    ]
    draft5 = service.create(uploader.identity, new_data)
    record5 = service.publish(uploader.identity, id_=draft5.id)._record

    # Verify PIDs were created for both schemes
    pids = PersistentIdentifier.query.filter(
        PersistentIdentifier.object_uuid == record5.pid.object_uuid,
        PersistentIdentifier.pid_type != record5.pid.pid_type,
    ).all()
    assert len(pids) == 2
    pid_types = {pid.pid_type for pid in pids}
    assert pid_types == {"cdsrn", "testrn"}

    # 5. Mixed mintable and non-mintable schemes
    new_data["metadata"]["identifiers"] = [
        {"scheme": "cdsrn", "identifier": "1234567894"},  # mintable
        {"scheme": "doi", "identifier": "10.1016/j.epsl.2011.11.037"},  # non-mintable
        {"scheme": "arxiv", "identifier": "arXiv:1310.2590"},  # non-mintable
    ]
    draft6 = service.create(uploader.identity, new_data)
    record6 = service.publish(uploader.identity, id_=draft6.id)._record

    # Verify only mintable scheme got PID created
    pids = PersistentIdentifier.query.filter(
        PersistentIdentifier.object_uuid == record6.pid.object_uuid,
        PersistentIdentifier.pid_type != record6.pid.pid_type,
    ).all()
    assert len(pids) == 1
    assert pids[0].pid_type == "cdsrn"
    assert pids[0].pid_value == "1234567894"

    # 6. Create a record with multiple identifiers
    new_data["metadata"]["identifiers"] = [
        {"scheme": "cdsrn", "identifier": "1234567895"},
        {"scheme": "testrn", "identifier": "1234567896"},
    ]
    draft7 = service.create(uploader.identity, new_data)
    record7 = service.publish(uploader.identity, id_=draft7.id)

    # Verify both PIDs were created
    pids_before = PersistentIdentifier.query.filter(
        PersistentIdentifier.object_uuid == record7._record.pid.object_uuid,
        PersistentIdentifier.pid_type != record7._record.pid.pid_type,
    ).all()
    assert len(pids_before) == 2
    pid_types_before = {pid.pid_type for pid in pids_before}
    assert pid_types_before == {"cdsrn", "testrn"}

    # 6. Test PID deletion: Remove one identifier and update draft
    draft7 = service.edit(uploader.identity, id_=record7.id)
    draft7.data["metadata"]["identifiers"] = [
        {"scheme": "cdsrn", "identifier": "1234567895"},  # Keep this one
        # Remove testrn identifier
    ]
    draft7 = service.update_draft(uploader.identity, id_=draft7.id, data=draft7.data)

    # Verify only one PID remains (deletion worked)
    pids_after_deletion = PersistentIdentifier.query.filter(
        PersistentIdentifier.object_uuid == draft7._record.pid.object_uuid,
        PersistentIdentifier.pid_type != draft7._record.pid.pid_type,
    ).all()
    assert len(pids_after_deletion) == 1
    assert pids_after_deletion[0].pid_type == "cdsrn"
    assert pids_after_deletion[0].pid_value == "1234567895"

    # 6. Test PID creation: Add a new identifier and update draft
    draft7.data["metadata"]["identifiers"] = [
        {"scheme": "cdsrn", "identifier": "1234567895"},  # Keep existing
        {"scheme": "testrn", "identifier": "1234567897"},  # Add new
    ]
    draft7 = service.update_draft(uploader.identity, id_=draft7.id, data=draft7.data)

    # Verify two PIDs exist now (creation worked)
    pids_after_creation = PersistentIdentifier.query.filter(
        PersistentIdentifier.object_uuid == draft7._record.pid.object_uuid,
        PersistentIdentifier.pid_type != draft7._record.pid.pid_type,
    ).all()
    assert len(pids_after_creation) == 2
    pid_types_after_creation = {pid.pid_type for pid in pids_after_creation}
    assert pid_types_after_creation == {"cdsrn", "testrn"}

    # 6. Test PID updates: Change an identifier value and update draft
    draft7.data["metadata"]["identifiers"] = [
        {"scheme": "cdsrn", "identifier": "1234567898"},  # Changed value
        {"scheme": "testrn", "identifier": "1234567897"},  # Keep this one
    ]
    draft7 = service.update_draft(uploader.identity, id_=draft7.id, data=draft7.data)

    # Verify old PID was deleted and new one was created (update worked)
    pids_after_update = PersistentIdentifier.query.filter(
        PersistentIdentifier.object_uuid == draft7._record.pid.object_uuid,
        PersistentIdentifier.pid_type != draft7._record.pid.pid_type,
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
    draft9.data["metadata"]["identifiers"] = [
        {
            "scheme": "cdsrn",
            "identifier": "1234567890",
        },  # This already exists from draft1
    ]
    draft9 = service.update_draft(uploader.identity, id_=draft9.id, data=draft9.data)
    assert len(draft9.errors) > 0

    # 8. Mintable(with validation errors) and non-mintable schemes
    draft10 = service.create(uploader.identity, minimal_restricted_record)
    draft10.data["metadata"]["identifiers"] = [
        {"scheme": "cdsrn", "identifier": "1234567890"},  # Already exists from draft1
        {"scheme": "arxiv", "identifier": "arXiv:1310.2590"},
    ]
    draft10 = service.update_draft(uploader.identity, id_=draft10.id, data=draft10.data)

    assert len(draft10.errors) > 0
    assert "already exists" in draft10.errors[0]["messages"][0]
    # Check if non-mintable scheme is saved in draft
    assert draft10.data["metadata"]["identifiers"] == [
        {"scheme": "cdsrn", "identifier": "1234567890"},
        {"scheme": "arxiv", "identifier": "arXiv:1310.2590"},
    ]
