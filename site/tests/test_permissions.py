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
from invenio_rdm_records.services.request_policies import FileModificationAdminPolicy
from invenio_records_resources.services.errors import PermissionDeniedError

from cds_rdm import generators
from cds_rdm.administration.permissions import harvester_admin_access_action
from cds_rdm.generators import HarvesterCurator
from cds_rdm.permissions import FileModificationHarvesterPolicy


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
                        {"term": {"user.id": "6"}},
                        {"term": {"action": "record.publish"}},
                    ]
                }
            },
        ),
        (set(), []),
    ],
)
def test_harvester_curator_permissions(monkeypatch, provides, expected_filter):
    """Harvester reports only include publishes by the dedicated harvester user."""
    monkeypatch.setattr(
        generators,
        "Permission",
        lambda *_: SimpleNamespace(
            allows=lambda i: harvester_admin_access_action in i.provides
        ),
    )
    monkeypatch.setattr(generators, "_harvester_user_id", lambda: "6")

    assert HarvesterCurator().needs() == [harvester_admin_access_action]

    identity = SimpleNamespace(provides=provides)

    query_filter = HarvesterCurator().query_filter(identity=identity)

    if expected_filter:
        assert query_filter.to_dict() == expected_filter
    else:
        assert query_filter == []


@pytest.fixture()
def admin_harvester_file_modification(app, monkeypatch):
    """Enable the admin and harvester policy for immediate file modification."""
    monkeypatch.setitem(
        app.config,
        "RDM_IMMEDIATE_FILE_MODIFICATION_POLICIES",
        [FileModificationAdminPolicy(), FileModificationHarvesterPolicy()],
    )


EXTERNAL_DOI = {"identifier": "10.1234/external", "provider": "external"}
# A CDS DOI is minted through the PIDs service
DATACITE_DOI = "datacite"


@pytest.mark.parametrize(
    ("user", "doi", "policy_cls"),
    [
        ("harvester_user", EXTERNAL_DOI, FileModificationHarvesterPolicy),
        ("harvester_user", DATACITE_DOI, None),
        ("harvester_user", None, None),
        ("admin", DATACITE_DOI, FileModificationAdminPolicy),
        ("admin", EXTERNAL_DOI, FileModificationAdminPolicy),
        ("admin", None, FileModificationAdminPolicy),
        ("uploader", EXTERNAL_DOI, None),
        ("uploader", DATACITE_DOI, None),
        ("uploader", None, None),
    ],
    ids=[
        "harvester-external-doi-accept",
        "harvester-datacite-doi-reject",
        "harvester-no-doi-reject",
        "admin-datacite-doi-accept",
        "admin-external-doi-accept",
        "admin-no-doi-accept",
        "submitter-external-doi-reject",
        "submitter-datacite-doi-reject",
        "submitter-no-doi-reject",
    ],
)
def test_file_modification_policies(
    request,
    admin_harvester_file_modification,
    db,
    uploader,
    minimal_restricted_record,
    user,
    doi,
    policy_cls,
):
    """Immediate file modification depending on the user and the record's DOI.

    ``policy_cls`` is the policy expected to allow the modification, or ``None``
    if the modification must be rejected.
    """
    service = current_rdm_records.records_service
    pids = {"doi": doi} if isinstance(doi, dict) else {}
    data = {**minimal_restricted_record, "pids": pids}
    draft = service.create(uploader.identity, data)
    if doi == DATACITE_DOI:
        service.pids.create(uploader.identity, draft.id, "doi", provider="datacite")
    record = service.publish(uploader.identity, draft.id)

    identity = request.getfixturevalue(user).identity
    policy_result = service.config.file_modification_policy.evaluate(
        identity, record._record
    )
    immediate = policy_result["immediate_file_modification"]

    assert immediate.enabled
    if policy_cls is None:
        assert not immediate.allowed
        assert immediate.policy is None
    else:
        assert immediate.allowed
        assert immediate.policy["id"] == policy_cls.id
