# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Task tests."""
from datetime import datetime, timedelta

import pytest
from invenio_access.permissions import system_identity
from invenio_accounts import testutils
from invenio_records_resources.proxies import current_service_registry
from invenio_vocabularies.contrib.names.api import Name

from cds_rdm.tasks import merge_duplicate_names_vocabulary, sync_local_accounts_to_names


@pytest.fixture(scope="function")
def user_1(app):
    """Create a user."""
    profile_1 = {
        "group": "CA",
        "orcid": "0000-0001-8135-3489",
        "mailbox": "92918",
        "section": "IR",
        "full_name": "Joe Doe",
        "person_id": "846610",
        "department": "IT",
        "given_name": "Joe",
        "family_name": "Doe",
        "affiliations": "CERN",
    }

    user_1 = testutils.create_test_user("joe@test.org", id=1, user_profile=profile_1)
    return user_1


@pytest.fixture(scope="function")
def user_2(app):
    """Create a user."""
    profile_2 = {
        "group": "CA",
        "mailbox": "92918",
        "section": "IR",
        "full_name": "Jane Doe",
        "person_id": "846611",
        "department": "IT",
        "given_name": "Jane",
        "family_name": "Doe",
        "affiliations": "CERN",
    }
    user_2 = testutils.create_test_user("jane2@test.org", id=2, user_profile=profile_2)
    return user_2


@pytest.fixture(scope="function")
def name_full_data():
    """Full name data."""
    return {
        "id": "0000-0001-8135-3489",
        "name": "Doe, John",
        "given_name": "John",
        "family_name": "Doe",
        "identifiers": [
            {"identifier": "0000-0001-8135-3489", "scheme": "orcid"},
            {"identifier": "gnd:4079154-3", "scheme": "gnd"},
        ],
        "affiliations": [{"name": "CustomORG"}],
    }


def test_sync_and_merge_local_accounts_to_names(
    app, db, user_1, user_2, name_full_data
):
    """Test sync local accounts to names."""
    since = (datetime.now() - timedelta(days=1)).isoformat()

    # Sync user 1 and user 2 to names
    sync_local_accounts_to_names(since)

    Name.index.refresh()

    service = current_service_registry.get("names")
    names = service.scan(system_identity)
    assert len(list(names.hits)) == 2

    name_1 = service.read(system_identity, user_1.get_id())
    name_2 = service.read(system_identity, user_2.get_id())

    assert name_1.data["given_name"] == user_1.user_profile["given_name"]
    assert name_1.data["family_name"] == user_1.user_profile["family_name"]
    assert name_2.data["given_name"] == user_2.user_profile["given_name"]
    assert name_2.data["family_name"] == user_2.user_profile["family_name"]

    # Creates a new name with same orcid as user_1
    item = service.create(system_identity, name_full_data)
    id_ = item.id
    Name.index.refresh()

    # Merge duplicate names based on ORCID
    merge_duplicate_names_vocabulary()

    Name.index.refresh()
    read_item = service.read(system_identity, id_)
    assert read_item.data["given_name"] == name_full_data["given_name"]
    assert read_item.data["family_name"] == name_full_data["family_name"]
    assert read_item.data["props"]["department"] == user_1.user_profile["department"]

    deprecated_name = service.read(system_identity, user_1.get_id())
    assert deprecated_name.data["tags"] == ["unlisted"]

    updated_name = service.read(system_identity, name_full_data["id"])
    assert updated_name.data["props"]["department"] == user_1.user_profile["department"]
    assert len(updated_name.data["affiliations"]) == 2
    assert {"name": "CERN"} in updated_name.data["affiliations"]
