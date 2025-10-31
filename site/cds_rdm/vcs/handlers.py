# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""GitLab OAuth handler override."""

from __future__ import annotations

from flask_login import current_user
from invenio_cern_sync.sso import cern_remote_app_name
from invenio_oauthclient import current_oauthclient

from cds_rdm.errors import (
    GitLabIdentityNotFoundError,
    KeycloakGitLabMismatchError,
    KeycloakIdentityNotFoundError,
)


def gitlab_account_info_serializer(original_serializer):
    """An OAuthClient account_info_serializer override for GitLab.

    This ensures that users who are logged into CDS with CERN Keycloak OAuth
    are also logged into GitLab with the same CERN Keycloak account to prevent
    an account mismatch that could cause bugs or security issues.
    """

    def inner(remote, resp, user_info, **kwargs):
        """Account info serializer."""
        # RemoteAccount only contains the application's OAuth Client ID so we need to find it
        cern_client_id = current_oauthclient.oauth.remote_apps.get(
            cern_remote_app_name
        ).consumer_key

        user_keycloak_id: str | None = None
        for remote_account in current_user.remote_accounts:
            if remote_account.client_id == cern_client_id:
                # This is the user's ID as stored in Keycloak, which is equivalent to the
                # CERN username of the person or their secondary account.
                user_keycloak_id = remote_account.extra_data.get("keycloak_id")

        if user_keycloak_id is None:
            # All non-administrative users are expected to have one.
            raise KeycloakIdentityNotFoundError(current_user.id)

        gl_user_id = str(user_info["id"])
        gl_identities = user_info["identities"]
        gl_extern_uid: str | None = None
        for identity in gl_identities:
            prov = identity["provider"]

            # On CERN GitLab, you have one GitLab account for each Keycloak account, with secondary accounts
            # being separate GitLab accounts. You can sign in to one account with either openid_connect or
            # kereberos, with the latter being used e.g. on CERN-provisioned computers.
            # If a user has only ever signed in on a CERN device they might only have the kerberos method
            # available, so we need to ensure we accept it.
            if prov == "openid_connect":
                gl_extern_uid = identity["extern_uid"]
            elif prov == "kerberos":
                # {'provider': 'kerberos', 'extern_uid': 'username@CERN.CH', 'saml_provider_id': None}
                gl_extern_uid = identity["extern_uid"].removesuffix("@CERN.CH")
            else:
                continue

        if gl_extern_uid is None:
            raise GitLabIdentityNotFoundError(gl_user_id)

        if user_keycloak_id != gl_extern_uid:
            raise KeycloakGitLabMismatchError(
                gl_user_id, gl_extern_uid, current_user.id, user_keycloak_id
            )

        # Continue with the rest of the account info serializer chain.
        return original_serializer(remote, resp, user_info, **kwargs)

    return inner
