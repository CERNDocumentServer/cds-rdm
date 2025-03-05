# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Task tests."""
from datetime import datetime, timedelta

from cds_rdm.tasks import sync_local_accounts_to_names
from invenio_access.permissions import system_identity
from invenio_records_resources.proxies import current_service_registry
from invenio_search.engine import dsl
from invenio_vocabularies.contrib.names.api import Name


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
    # Creates the CDS name unlisted and the ORCID name
    assert len(list(names.hits)) == 2

    cds_name = service.read(system_identity, user_3.user_profile["person_id"])
    assert cds_name.data["tags"] == ["unlisted"]

    filter = dsl.Q(
        "bool",
        must=[
            dsl.Q("term", **{"props.user_id": str(user_3.get_id())}),
        ],
    )

    os_name = service.search(system_identity, extra_filter=filter)
    assert os_name.total == 2

    name = service.read(system_identity, id_)

    # Orcid value got updated
    assert name.data["given_name"] == user_3.user_profile["given_name"]
    assert name.data["family_name"] == user_3.user_profile["family_name"]
    assert name.data["props"]["department"] == user_3.user_profile["department"]
    assert name.data["props"]["user_id"] == user_3.get_id()
    assert len(name.data["affiliations"]) == 1
    assert {"name": "CERN"} in name.data["affiliations"]
    # ORCID identifier
    assert len(name.data["identifiers"]) == 1
