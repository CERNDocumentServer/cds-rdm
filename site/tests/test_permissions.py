# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Permissions tests."""
from types import SimpleNamespace

import pytest
from invenio_rdm_records.proxies import current_rdm_records
from invenio_rdm_records.records.api import RDMDraft, RDMParent, RDMRecord
from invenio_records_resources.services.errors import PermissionDeniedError

from cds_rdm import generators
from cds_rdm.administration.permissions import harvester_admin_access_action
from cds_rdm.generators import HarvesterCurator


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


@pytest.mark.parametrize(
    ("provides", "expected_filter"),
    [
        (
            {harvester_admin_access_action},
            {
                "bool": {
                    "must": [
                        {"term": {"user.id": "system"}},
                        {"term": {"action": "record.publish"}},
                    ]
                }
            },
        ),
        (set(), []),
    ],
)
def test_harvester_curator_permissions(monkeypatch, provides, expected_filter):
    """Harvester permissions use the action need and filter system logs only."""
    monkeypatch.setattr(
        generators,
        "Permission",
        lambda *_: SimpleNamespace(
            allows=lambda i: harvester_admin_access_action in i.provides
        ),
    )

    assert HarvesterCurator().needs() == [harvester_admin_access_action]

    identity = SimpleNamespace(provides=provides)

    query_filter = HarvesterCurator().query_filter(identity=identity)

    if expected_filter:
        assert query_filter.to_dict() == expected_filter
    else:
        assert query_filter == []
