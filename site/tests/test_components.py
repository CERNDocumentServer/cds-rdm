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
from invenio_pidstore.models import PersistentIdentifier, PIDStatus
from invenio_rdm_records.proxies import current_rdm_records
from invenio_rdm_records.services.components import DefaultRecordsComponents
from invenio_rdm_records.services.pids.providers import (
    DataCiteClient,
    DataCitePIDProvider,
)
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
    3. Mixed mintable and non-mintable schemes
    4. PID lifecycle management (deletion, creation, updates)
    5. Duplicate validation
    6. Mixed mintable(with validation errors) and non-mintable schemes
    7. Mixed mintable identifiers with other minted PIDs like DOI
    8. Same identifier, different record versions (deletion, creation, updates)
    """

    client = uploader.login(client)
    service = current_rdm_records.records_service

    monkeypatch.setitem(
        current_app.config,
        "RDM_RECORDS_IDENTIFIERS_SCHEMES",
        {
            **current_app.config["RDM_RECORDS_IDENTIFIERS_SCHEMES"],
            "cdsrn": {
                "label": "CDS Report Number",
                "validator": lambda x: True,
                "datacite": "CDS",
            },
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
        PersistentIdentifier.object_uuid == record1.parent.id,
        PersistentIdentifier.pid_type == "cdsrn",
        PersistentIdentifier.pid_value == "1234567890",
    ).all()
    assert len(pids) == 1
    assert pids[0].status == PIDStatus.REGISTERED

    # 2. Test update_draft method with duplicate identifier
    draft2 = service.create(uploader.identity, new_data)
    # Re-use the same draft data to test the duplicate validation
    assert len(draft2.errors) > 0
    assert "already taken" in draft2.errors[0]["messages"][0]

    # 2. Test update_draft with valid new identifier
    draft3 = service.create(uploader.identity, minimal_restricted_record)
    draft3.data["metadata"]["identifiers"] = [
        {"scheme": "cdsrn", "identifier": "1234567901"},  # New unique identifier
    ]
    draft3 = service.update_draft(uploader.identity, id_=draft3.id, data=draft3.data)
    assert len(draft3.errors) == 0

    # 3. Mixed mintable and non-mintable schemes
    new_data["metadata"]["identifiers"] = [
        {"scheme": "cdsrn", "identifier": "1234567894"},  # mintable
        {"scheme": "doi", "identifier": "10.1016/j.epsl.2011.11.037"},  # non-mintable
        {"scheme": "arxiv", "identifier": "arXiv:1310.2590"},  # non-mintable
    ]
    draft6 = service.create(uploader.identity, new_data)
    record6 = service.publish(uploader.identity, id_=draft6.id)._record

    # Verify only mintable scheme got PID created
    pids = PersistentIdentifier.query.filter(
        PersistentIdentifier.object_uuid == record6.parent.id,
        PersistentIdentifier.pid_type != "recid",
    ).all()
    assert len(pids) == 1
    assert pids[0].pid_type == "cdsrn"
    assert pids[0].pid_value == "1234567894"

    # 4. Create a record with multiple identifiers
    new_data["metadata"]["identifiers"] = [
        {"scheme": "cdsrn", "identifier": "1234567895"},
        {"scheme": "cdsrn", "identifier": "1234567896"},
    ]
    draft7 = service.create(uploader.identity, new_data)
    record7 = service.publish(uploader.identity, id_=draft7.id)

    # Verify both PIDs were created
    pids_before = PersistentIdentifier.query.filter(
        PersistentIdentifier.object_uuid == record7._record.parent.id,
    ).all()
    assert len(pids_before) == 3
    assert {pid.pid_type for pid in pids_before} == {"cdsrn", "recid"}

    # 4. Test PID deletion: Remove one identifier and publish
    draft7 = service.edit(uploader.identity, id_=record7.id)
    draft7.data["metadata"]["identifiers"] = [
        {"scheme": "cdsrn", "identifier": "1234567895"},  # Keep this one
        # Remove cdsrn identifier
    ]
    draft7 = service.update_draft(uploader.identity, id_=draft7.id, data=draft7.data)
    record7 = service.publish(uploader.identity, id_=draft7.id)

    # Verify only one PID remains (deletion worked)
    pids_after_deletion = PersistentIdentifier.query.filter(
        PersistentIdentifier.object_uuid == record7._record.parent.id,
    ).all()
    assert len(pids_after_deletion) == 2
    assert {pid.pid_type for pid in pids_after_deletion} == {
        "cdsrn",
        "recid",
    }  # recid is not deleted

    # 4. Test PID creation: Add a new identifier and update draft
    draft7 = service.edit(uploader.identity, id_=record7.id)
    draft7.data["metadata"]["identifiers"] = [
        {"scheme": "cdsrn", "identifier": "1234567895"},  # Keep existing
        {"scheme": "cdsrn", "identifier": "1234567897"},  # Add new
    ]
    draft7 = service.update_draft(uploader.identity, id_=draft7.id, data=draft7.data)

    # Verify two PIDs exist now (creation worked)
    pids_after_creation = PersistentIdentifier.query.filter(
        PersistentIdentifier.object_uuid == draft7._record.parent.id,
    ).all()
    assert len(pids_after_creation) == 3
    pid_types_after_creation = {
        (pid.pid_value, pid.status.value) for pid in pids_after_creation
    }
    assert pid_types_after_creation == {
        ("1234567895", PIDStatus.REGISTERED.value),
        ("1234567897", PIDStatus.RESERVED.value),
        (draft7._record.parent.pid.pid_value, PIDStatus.REGISTERED.value),
    }

    # 4. Test PID updates: Change an identifier value and publish
    draft7.data["metadata"]["identifiers"] = [
        {"scheme": "cdsrn", "identifier": "1234567895"},  # Keep this one
        {"scheme": "cdsrn", "identifier": "1234567898"},  # Change value
    ]
    draft7 = service.update_draft(uploader.identity, id_=draft7.id, data=draft7.data)
    record7 = service.publish(uploader.identity, id_=draft7.id)

    # Verify old PID was deleted and new one was created (update worked)
    pids_after_update = PersistentIdentifier.query.filter(
        PersistentIdentifier.object_uuid == record7._record.parent.id,
    ).all()
    assert len(pids_after_update) == 3
    assert {(pid.pid_value, pid.status.value) for pid in pids_after_update} == {
        ("1234567895", PIDStatus.REGISTERED.value),
        ("1234567898", PIDStatus.REGISTERED.value),
        (record7._record.parent.pid.pid_value, PIDStatus.REGISTERED.value),
    }

    # 5. Duplicate validation
    draft9 = service.create(uploader.identity, minimal_restricted_record)
    draft9.data["metadata"]["identifiers"] = [
        {
            "scheme": "cdsrn",
            "identifier": "1234567890",
        },  # This already exists from draft1
    ]
    draft9 = service.update_draft(uploader.identity, id_=draft9.id, data=draft9.data)
    assert len(draft9.errors) > 0

    # 6. Mintable(with validation errors) and non-mintable schemes
    draft10 = service.create(uploader.identity, minimal_restricted_record)
    draft10.data["metadata"]["identifiers"] = [
        {"scheme": "cdsrn", "identifier": "1234567890"},  # Already exists from draft1
        {"scheme": "arxiv", "identifier": "arXiv:1310.2590"},
    ]
    draft10 = service.update_draft(uploader.identity, id_=draft10.id, data=draft10.data)

    assert len(draft10.errors) > 0
    assert "already taken" in draft10.errors[0]["messages"][0]
    # Check if non-mintable scheme is saved in draft
    assert draft10.data["metadata"]["identifiers"] == [
        {"scheme": "cdsrn", "identifier": "1234567890"},
        {"scheme": "arxiv", "identifier": "arXiv:1310.2590"},
    ]

    # 7. Mintable identifiers with other minted PIDs like DOI, etc.
    monkeypatch.setitem(
        current_app.config,
        "DATACITE_PREFIX",
        "10.1000",
    )
    datacite_client = DataCiteClient("datacite")
    datacite_provider = DataCitePIDProvider("datacite", client=datacite_client)

    draft11 = service.create(uploader.identity, minimal_restricted_record)
    draft11.data["metadata"]["identifiers"] = [
        {"scheme": "cdsrn", "identifier": "1234567899"},
        {"scheme": "cdsrn", "identifier": "1234567800"},
    ]
    draft11 = service.update_draft(uploader.identity, id_=draft11.id, data=draft11.data)
    record11 = service.publish(uploader.identity, id_=draft11.id)
    datacite_provider.create(record11._record)

    draft11 = service.edit(uploader.identity, id_=record11.id)
    draft11.data["metadata"]["identifiers"] = [
        {"scheme": "cdsrn", "identifier": "1234567800"},
    ]  # Remove an identifier
    draft11 = service.update_draft(uploader.identity, id_=draft11.id, data=draft11.data)
    record11 = service.publish(uploader.identity, id_=draft11.id)

    # Verify other PIDs were not deleted
    pids_after_update = PersistentIdentifier.query.filter(
        PersistentIdentifier.object_uuid.in_(
            [record11._record.pid.object_uuid, record11._record.parent.id]
        ),
    ).all()
    assert len(pids_after_update) == 4
    pids_after_update = {
        (pid.pid_type, pid.pid_value, pid.object_uuid) for pid in pids_after_update
    }
    assert pids_after_update == {
        ("doi", f"10.1000/{record11.id}", record11._record.pid.object_uuid),
        ("recid", record11.id, record11._record.pid.object_uuid),
        ("recid", record11._record.parent.pid.pid_value, record11._record.parent.id),
        ("cdsrn", "1234567800", record11._record.parent.id),
    }

    # 8. Same identifier, different record versions (deletion, creation, updates)
    draft12 = service.create(uploader.identity, minimal_restricted_record)
    draft12.data["metadata"]["identifiers"] = [
        {"scheme": "cdsrn", "identifier": "CERN-REPORT-1234567890"},
        {"scheme": "cdsrn", "identifier": "CERN-REPORT-1234567891"},
    ]
    draft12 = service.update_draft(uploader.identity, id_=draft12.id, data=draft12.data)

    # Verify both PIDs were reserved
    pids_after_creation = PersistentIdentifier.query.filter(
        PersistentIdentifier.object_uuid == draft12._record.parent.id,
        PersistentIdentifier.status == PIDStatus.RESERVED,
        PersistentIdentifier.pid_type != "recid",
    ).all()
    assert len(pids_after_creation) == 2
    pid_values_after_creation = {pid.pid_value for pid in pids_after_creation}
    assert pid_values_after_creation == {
        "CERN-REPORT-1234567890",
        "CERN-REPORT-1234567891",
    }

    # Publish the record - Register the PIDs
    record12 = service.publish(uploader.identity, id_=draft12.id)

    # Verify both PIDs were registered
    pids_after_publication = PersistentIdentifier.query.filter(
        PersistentIdentifier.object_uuid == record12._record.parent.id,
        PersistentIdentifier.status == PIDStatus.REGISTERED,
        PersistentIdentifier.pid_type != "recid",
    ).all()
    assert len(pids_after_publication) == 2
    pid_values_after_publish = {pid.pid_value for pid in pids_after_publication}
    assert pid_values_after_publish == {
        "CERN-REPORT-1234567890",
        "CERN-REPORT-1234567891",
    }

    draft13 = service.new_version(uploader.identity, record12.id)
    draft13.data["metadata"]["publication_date"] = "2026-01-01"
    draft13.data["metadata"]["identifiers"] = [
        {
            "scheme": "cdsrn",
            "identifier": "CERN-REPORT-1234567890",
        },  # Can re-use the same identifier
        {"scheme": "cdsrn", "identifier": "CERN-REPORT-1234567892"},  # New identifier
    ]
    draft13 = service.update_draft(uploader.identity, id_=draft13.id, data=draft13.data)
    record13 = service.publish(uploader.identity, id_=draft13.id)

    # Verify new PID was created and old PID stayed registered
    pids_after_creation = PersistentIdentifier.query.filter(
        PersistentIdentifier.object_uuid == draft13._record.parent.id,
        PersistentIdentifier.status == PIDStatus.REGISTERED,
        PersistentIdentifier.pid_type != "recid",
    ).all()
    assert {pid.pid_value for pid in pids_after_creation} == {
        "CERN-REPORT-1234567890",
        "CERN-REPORT-1234567891",
        "CERN-REPORT-1234567892",
    }

    draft12 = service.edit(uploader.identity, id_=record12.id)
    draft12.data["metadata"]["identifiers"] = [
        {
            "scheme": "cdsrn",
            "identifier": "CERN-REPORT-1234567892",
        },  # Remove CERN-REPORT-1234567891 PID
    ]
    draft12 = service.update_draft(uploader.identity, id_=draft12.id, data=draft12.data)
    # Verify CERN-REPORT-1234567891 PID stayed registered, since it is a draft edit
    pids_after_update = PersistentIdentifier.query.filter(
        PersistentIdentifier.object_uuid == draft12._record.parent.id,
        PersistentIdentifier.status == PIDStatus.REGISTERED,
        PersistentIdentifier.pid_type != "recid",
    ).all()
    assert {pid.pid_value for pid in pids_after_update} == {
        "CERN-REPORT-1234567890",
        "CERN-REPORT-1234567891",
        "CERN-REPORT-1234567892",
    }

    record12 = service.publish(uploader.identity, id_=draft12.id)
    # Verify CERN-REPORT-1234567891 PID was deleted and CERN-REPORT-1234567890 PID stayed registered
    pids_after_publish = PersistentIdentifier.query.filter(
        PersistentIdentifier.object_uuid == record12._record.parent.id,
        PersistentIdentifier.status == PIDStatus.REGISTERED,
        PersistentIdentifier.pid_type != "recid",
    ).all()
    assert {pid.pid_value for pid in pids_after_publish} == {
        "CERN-REPORT-1234567890",
        "CERN-REPORT-1234567892",
    }
