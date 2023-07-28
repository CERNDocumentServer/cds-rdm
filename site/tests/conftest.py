# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Pytest fixtures."""

import pytest
from invenio_app.factory import create_api

from cds_rdm.permissions import CDSCommunitiesPermissionPolicy


@pytest.fixture(scope="module")
def app_config(app_config):
    """Mimic an instance's configuration."""
    app_config["REST_CSRF_ENABLED"] = True
    app_config["DATACITE_ENABLED"] = True
    app_config["DATACITE_PREFIX"] = "10.17181"
    app_config["OAUTH_REMOTE_APP_NAME"] = "cern"
    app_config["CERN_APP_CREDENTIALS"] = {
        "consumer_key": "CHANGE ME",
        "consumer_secret": "CHANGE ME",
    }
    app_config["CERN_LDAP_URL"] = ""  # mock
    app_config["COMMUNITIES_PERMISSION_POLICY"] = CDSCommunitiesPermissionPolicy
    app_config["COMMUNITIES_ALLOW_RESTRICTED"] = True
    app_config["CDS_GROUPS_ALLOW_CREATE_COMMUNITIES"] = [
        "group-allowed-create-communities"
    ]
    return app_config


@pytest.fixture(scope="module")
def create_app():
    """Create test app."""
    return create_api
