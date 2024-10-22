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


def test_legacy_redirection(uploader, client, minimal_record_with_files, add_pid):

    client = uploader.login(client)
    service = current_rdm_records.records_service
    draft_file_service = service.draft_files
    # create draft
    draft = service.create(uploader.identity, minimal_record_with_files)
    file_id = "test.pdf"
    # add file to draft
    draft_file_service.init_files(uploader.identity, draft.id, data=[{"key": file_id}])
    draft_file_service.set_file_content(
        uploader.identity, draft.id, file_id, BytesIO(b"test file content")
    )
    draft_file_service.commit_file(uploader.identity, draft.id, file_id)
    # publish record with file
    record = service.publish(uploader.identity, draft.id)
    RDMRecord.index.refresh()

    # Add legacy pid to pidstore
    draft_pid = recid = PersistentIdentifier.query.filter_by(
        pid_value=draft.id, pid_type="recid"
    ).one()
    pid = add_pid(
        pid_type=LEGACY_RECID_PID_TYPE,
        pid_value=LEGACY_RECID,
        object_uuid=draft_pid.object_uuid,
    )

    rdm_record_url = record_url_for(pid_value=record.id)

    # Test record redirection
    response = client.get("/record/123456")
    assert response.status_code == 302
    assert rdm_record_url in response.location

    response = client.get("/record/123456?test=check&foo=bar")
    assert response.status_code == 302

    # Test not found case
    response = client.get("/record/654321")
    assert response.status_code == 404

    # Test files redirection
    response = client.get("/record/123456/files/test.pdf")
    assert response.status_code == 302

    response = client.get("/record/123456/files/")
    assert response.status_code == 302

    response = client.get("/record/123456/files/test.pdf?test=check&foo=bar")
    assert response.status_code == 302
