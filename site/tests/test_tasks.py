# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Task tests."""
from datetime import datetime, timedelta

from invenio_access.permissions import system_identity
from invenio_records_resources.proxies import current_service_registry
from invenio_vocabularies.contrib.names.api import Name

from cds_rdm.tasks import merge_duplicate_names_vocabulary, sync_local_accounts_to_names


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

    name_1 = service.read(system_identity, user_1.user_profile["person_id"])
    name_2 = service.read(system_identity, user_2.user_profile["person_id"])

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

    deprecated_name = service.read(system_identity, user_1.user_profile["person_id"])
    assert deprecated_name.data["tags"] == ["unlisted"]

    updated_name = service.read(system_identity, name_full_data["id"])
    assert updated_name.data["props"]["department"] == user_1.user_profile["department"]
    assert len(updated_name.data["affiliations"]) == 2
    assert {"name": "CERN"} in updated_name.data["affiliations"]
