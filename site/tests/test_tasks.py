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
from invenio_search.engine import dsl
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
def user_3(app):
    """Create a user."""
    profile_3 = {
        "group": "CA",
        "mailbox": "92918",
        "orcid": "0009-0007-7638-4652",
        "section": "IR",
        "full_name": "John Doe",
        "person_id": "846612",
        "department": "IT",
        "given_name": "John",
        "family_name": "Doe",
        "affiliations": "CERN",
    }
    user_3 = testutils.create_test_user("john@test.org", id=3, user_profile=profile_3)
    return user_3


@pytest.fixture(scope="function")
def name_user_3():
    """Name data."""
    return {
        "id": "0009-0007-7638-4652",
        "name": "Doe, John",
        "given_name": "John",
        "family_name": "Doe",
        "identifiers": [
            {"identifier": "0009-0007-7638-4652", "scheme": "orcid"},
        ],
        "affiliations": [{"name": "CERN"}],
    }


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
    app, database, user_1, user_2, name_full_data
):
    """Test sync local accounts to names."""
    since = (datetime.now() - timedelta(days=1)).isoformat()

    # Sync user 1 and user 2 to names
    sync_local_accounts_to_names(since)

    Name.index.refresh()

    service = current_service_registry.get("names")
    names = service.scan(system_identity)
    assert len(list(names.hits)) == 2

    filter_1 = dsl.Q(
        "bool",
        must=[
            dsl.Q("term", **{"props.user_id": str(user_1.get_id())}),
            dsl.Q("prefix", id="cds:a:"),
        ],
    )
    os_name_1 = next(service.search(system_identity, extra_filter=filter_1).hits)

    filter_2 = dsl.Q(
        "bool",
        must=[
            dsl.Q("term", **{"props.user_id": str(user_2.get_id())}),
            dsl.Q("prefix", id="cds:a:"),
        ],
    )
    os_name_2 = next(service.search(system_identity, extra_filter=filter_2).hits)

    name_1 = service.read(system_identity, os_name_1.get("id"))
    name_2 = service.read(system_identity, os_name_2.get("id"))

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

    deprecated_name = service.read(system_identity, os_name_1.get("id"))
    assert deprecated_name.data["tags"] == ["unlisted"]

    updated_name = service.read(system_identity, name_full_data["id"])
    assert updated_name.data["props"]["department"] == user_1.user_profile["department"]
    assert len(updated_name.data["affiliations"]) == 2
    assert {"name": "CERN"} in updated_name.data["affiliations"]


def test_sync_name_with_existing_orcid(app, database, user_3, name_user_3):
    """Test sync name with existing ORCID."""
    service = current_service_registry.get("names")

    # Creates a new name with same orcid as user_3
    item = service.create(system_identity, name_user_3)
    id_ = item.id
    Name.index.refresh()

    since = (datetime.now() - timedelta(days=1)).isoformat()
    # Sync user 3 to names
    sync_local_accounts_to_names(since)

    Name.index.refresh()

    names = service.scan(system_identity)
    # 3 created in previous test + 1 new
    assert len(list(names.hits)) == 4

    filter = dsl.Q(
        "bool",
        must=[
            dsl.Q("term", **{"props.user_id": str(user_3.get_id())}),
            dsl.Q("prefix", id="cds:a:"),
        ],
    )

    # Since the ORCID value is present no CDS name is created but the user data is merged to the ORCID one
    os_name = service.search(system_identity, extra_filter=filter)
    assert os_name.total == 0

    name = service.read(system_identity, id_)

    # Orcid value got updated
    assert name.data["given_name"] == user_3.user_profile["given_name"]
    assert name.data["family_name"] == user_3.user_profile["family_name"]
    assert name.data["props"]["department"] == user_3.user_profile["department"]
    assert name.data["props"]["user_id"] == user_3.get_id()
    assert len(name.data["affiliations"]) == 1
    assert {"name": "CERN"} in name.data["affiliations"]
    # ORCID identifier + CDS identifier
    assert len(name.data["identifiers"]) == 2
