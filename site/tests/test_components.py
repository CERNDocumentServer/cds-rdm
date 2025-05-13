# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.
"""Test components."""


from copy import deepcopy

import pytest
from invenio_rdm_records.proxies import current_rdm_records
from marshmallow import ValidationError

from cds_rdm.components import SubjectsValidationComponent


def test_subjects_validation_component_update_draft(
    minimal_record_with_files, uploader, client
):
    """Test the metadata component."""
    client = uploader.login(client)
    service = current_rdm_records.records_service
    # create draft
    draft = service.create(uploader.identity, minimal_record_with_files)._record

    component = SubjectsValidationComponent(current_rdm_records.records_service)

    new_data = deepcopy(minimal_record_with_files)
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
    new_data = deepcopy(minimal_record_with_files)
    new_data["metadata"]["subjects"] = []
    with pytest.raises(ValidationError):
        component.update_draft(uploader.identity, data=new_data, record=draft)


def test_subjects_validation_component_update_draft_admin(
    minimal_record_with_files, uploader, client, administrator
):
    """Test the metadata component."""
    client = uploader.login(client)
    service = current_rdm_records.records_service
    # create draft
    draft = service.create(uploader.identity, minimal_record_with_files)._record

    component = SubjectsValidationComponent(current_rdm_records.records_service)

    new_data = deepcopy(minimal_record_with_files)
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
    new_data = deepcopy(minimal_record_with_files)
    new_data["metadata"]["subjects"] = []
    assert (
        component.update_draft(administrator.identity, data=new_data, record=draft)
        == None
    )
