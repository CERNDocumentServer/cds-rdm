# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 CERN.
#
# Invenio-RDM is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.


from io import BytesIO

import pytest
from invenio_pidstore.models import PersistentIdentifier
from invenio_rdm_records.proxies import current_rdm_records
from invenio_rdm_records.records.api import RDMRecord
from invenio_rdm_records.resources.urls import record_url_for

LEGACY_RECID = "123456"
LEGACY_RECID_PID_TYPE = "lrecid"


def add_file_to_draft(draft_file_service, uploader, draft, file_id):
    """Add file to draft record."""
    draft_file_service.init_files(uploader.identity, draft.id, data=[{"key": file_id}])
    draft_file_service.set_file_content(
        uploader.identity, draft.id, file_id, BytesIO(b"test file content")
    )
    draft_file_service.commit_file(uploader.identity, draft.id, file_id)


def test_legacy_redirection(uploader, client, minimal_record_with_files, add_pid):
    """Test legacy redirection mechanism."""
    client = uploader.login(client)
    service = current_rdm_records.records_service
    # create draft
    draft = service.create(uploader.identity, minimal_record_with_files)
    add_file_to_draft(service.draft_files, uploader, draft, "test.pdf")
    # publish record with file
    record = service.publish(uploader.identity, draft.id)
    RDMRecord.index.refresh()

    # Add legacy pid to pidstore mapped to parent pid
    parent = draft._record.parent
    parent_pid = PersistentIdentifier.query.filter_by(
        pid_value=parent.pid.pid_value, pid_type="recid"
    ).one()
    add_pid(
        pid_type=LEGACY_RECID_PID_TYPE,
        pid_value=LEGACY_RECID,
        object_uuid=parent_pid.object_uuid,
    )

    rdm_record_url = "/records/" + record.id

    # Test record redirection
    response = client.get("/record/123456")
    assert response.status_code == 302
    # Resolves to parent, so get response from /records/parent_pid
    response = client.get(response.location)
    assert response.status_code == 302
    assert response.location == rdm_record_url

    query_params = "?test=check&foo=bar"
    response = client.get("/record/123456" + query_params)
    assert response.status_code == 302
    # Resolves to parent, so get response from /records/parent_pid
    response = client.get(response.location)
    assert response.status_code == 302
    assert response.location == rdm_record_url

    # Test not found case
    response = client.get("/record/654321")
    assert response.status_code == 404

    # Test files redirection
    file_route = "/preview/test.pdf"
    response = client.get("/record/123456/files/test.pdf")
    assert response.status_code == 302
    assert response.location == rdm_record_url + file_route

    response = client.get("/record/123456/files/")
    assert response.status_code == 302
    # Resolves to parent, so get response from /records/parent_pid
    response = client.get(response.location)
    assert response.status_code == 302
    assert response.location == rdm_record_url

    response = client.get("/record/123456/files/test.pdf" + query_params)
    assert response.status_code == 302
    assert response.location == rdm_record_url + file_route + query_params

    # Add new version of record
    draft_v2 = service.new_version(uploader.identity, draft.id)
    service.update_draft(uploader.identity, draft_v2.id, minimal_record_with_files)
    add_file_to_draft(service.draft_files, uploader, draft_v2, "test_v2.pdf")
    record_v2 = service.publish(uploader.identity, draft_v2.id)

    rdm_record_v2_url = "/records/" + record_v2.id

    # Always redirect to latest version
    response = client.get("/record/123456")
    assert response.status_code == 302
    # Resolves to parent, so get response from /records/parent_pid
    response = client.get(response.location)
    assert response.status_code == 302
    assert response.location == rdm_record_v2_url

    # Test files redirection without version
    file_route_v2 = "/preview/test_v2.pdf"
    response = client.get("/record/123456/files/test_v2.pdf" + query_params)
    assert response.status_code == 302
    assert response.location == rdm_record_v2_url + file_route_v2 + query_params

    # Test files redirection with version
    response = client.get("/record/123456/files/test.pdf?version=1")
    assert response.status_code == 302
    assert response.location == rdm_record_url + file_route

    response = client.get("/record/123456/files/test.pdf?version=2")
    assert response.status_code == 302
    assert response.location == rdm_record_v2_url + file_route

    # v3 doesn't exist, resolves to latest
    response = client.get("/record/123456/files/test_v2.pdf?version=3")
    assert response.status_code == 302
    assert response.location == rdm_record_v2_url + file_route_v2

    # files download redirection case
    response = client.get("/record/123456/files/allfiles-small" + query_params)
    assert response.status_code == 302
    assert response.location == record_v2.links["archive"]