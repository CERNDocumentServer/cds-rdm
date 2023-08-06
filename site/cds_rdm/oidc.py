# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2023 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""OIDC settings."""

from flask import current_app, g
from invenio_db import db
from invenio_oauthclient import current_oauthclient, oauth_link_external_id
from invenio_oauthclient.contrib.keycloak.handlers import get_user_info
from invenio_userprofiles.forms import confirm_register_form_preferences_factory
from werkzeug.local import LocalProxy

_security = LocalProxy(lambda: current_app.extensions["security"])


def confirm_registration_form(*args, **kwargs):
    """Confirm form."""
    Form = confirm_register_form_preferences_factory(_security.confirm_register_form)

    class _Form(Form):
        password = None
        recaptcha = None
        submit = None  # defined in the template

    return _Form(*args, **kwargs)


def cern_groups_serializer(remote, groups, **kwargs):
    """Serialize the groups response object."""
    serialized_groups = []
    # E-groups do have unique names and this name cannot be updated,
    # therefore the name can act as an ID for invenio
    for group_name in groups:
        serialized_groups.append({"id": group_name, "name": group_name})

    return serialized_groups


def cern_setup_handler(remote, token, resp):
    """Perform additional setup after the user has been logged in."""
    token_user_info, _ = get_user_info(remote, resp)

    with db.session.begin_nested():
        # fetch the user's Keycloak ID and set it in extra_data
        keycloak_id = token_user_info["sub"]
        cern_person_id = token_user_info["cern_person_id"]
        token.remote_account.extra_data = {
            "keycloak_id": keycloak_id,
            "person_id": cern_person_id,  # Required to properly sync the users
        }

        user = token.remote_account.user
        external_id = {"id": keycloak_id, "method": remote.name}

        # link account with external Keycloak ID
        oauth_link_external_id(user, external_id)


def cern_groups_handler(remote, resp):
    """Retrieves groups from remote account.

    Groups are already part of the response token
    """
    groups = g.pop("_cern_groups", [])
    handlers = current_oauthclient.signup_handlers[remote.name]
    # `remote` param automatically injected via `make_handler` helper
    return handlers["groups_serializer"](groups)


def cern_info_handler(remote, resp):
    """Info handler."""
    token_user_info, user_info = get_user_info(remote, resp)

    # Add the user_info to the request, so it can be used in the groups handler
    # to avoid yet another request to the user info endpoint
    g._cern_groups = user_info.get("groups", [])

    handlers = current_oauthclient.signup_handlers[remote.name]
    return handlers["info_serializer"](resp, token_user_info, user_info)


def cern_info_serializer(remote, resp, token_user_info, user_info):
    """Info serializer."""
    user_info = user_info or {}

    email = token_user_info["email"]
    full_name = token_user_info["name"]
    username = token_user_info["preferred_username"]
    external_id = token_user_info["cern_upn"]
    affiliations = user_info.get("home_institute", "")
    return {
        "user": {
            "active": True,
            "email": email,
            "profile": {
                "full_name": full_name,
                "username": username,
                "affiliations": affiliations,
            },
            "prefs": {
                "visibility": "public",
                "email_visibility": "restricted",
                "locale": "en",
            },
        },
        "external_id": external_id,
        "external_method": remote.name,
    }
