# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Permissions tests."""
import pytest
from invenio_rdm_records.proxies import current_rdm_records
from invenio_rdm_records.records.api import RDMDraft, RDMParent, RDMRecord
from invenio_records_resources.services.errors import PermissionDeniedError


def test_archiver_permissions(
    db, app, minimal_restricted_record, uploader, client, headers, archiver
):
    """Check the permissions of the archiver."""
    service = current_rdm_records.records_service
    draft = service.create(uploader.identity, minimal_restricted_record)
    recid = draft.id
    r = service.publish(uploader.identity, draft.id)
    RDMRecord.index.refresh()

    with pytest.raises(PermissionDeniedError):
        new_draft = service.edit(archiver.identity, recid)

    with pytest.raises(PermissionDeniedError):
        deleted = service.delete(archiver.identity, recid)

    with pytest.raises(PermissionDeniedError):
        create = service.create(archiver.identity, minimal_restricted_record)

    results = service.search(archiver.identity)
    assert results.total == 1
    assert results.to_dict()["hits"]["hits"][0]["id"] == recid
