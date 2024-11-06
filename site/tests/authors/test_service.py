# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Tests for services."""
import pytest
from invenio_access.permissions import system_identity

from cds_rdm.proxies import current_authors_service


@pytest.fixture()
def authors_service(running_app):
    """Service fixture."""
    return current_authors_service


@pytest.fixture()
def author_data():
    """Author data."""
    return {
        "given_name": "John",
        "family_name": "Doe",
    }


def test_create_update(app, db, authors_service, author_data):
    """Test create and update authors."""
    # Create
    item = authors_service.create(system_identity, author_data)

    assert item["given_name"] == author_data["given_name"]
    assert item["family_name"] == author_data["family_name"]
    assert item.pid

    # Read
    item = authors_service.read(system_identity, item.pid.pid_value)
    assert item["given_name"] == "John"

    # Update
    item = authors_service.update(
        system_identity,
        item.pid.pid_value,
        {"given_name": "Jane", "family_name": "Doe"},
    )
    assert item["given_name"] == "Jane"

    # Read
    item = authors_service.read(system_identity, item.pid.pid_value)
    assert item["given_name"] == "Jane"
