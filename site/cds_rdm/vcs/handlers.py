# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""GitLab OAuth handler override."""

from __future__ import annotations

from flask_login import current_user

from cds_rdm.errors import (
    GitLabIdentityNotFoundError,
    KeycloakGitLabMismatchError,
)


def gitlab_account_info_serializer(original_serializer):
    """An OAuthClient account_info_serializer override for GitLab.

    This ensures that users who are logged into CDS with CERN Keycloak OAuth
    are also logged into GitLab with the same CERN Keycloak account to prevent
    an account mismatch that could cause bugs or security issues.
    """

    def inner(remote, resp, user_info, **kwargs):
        """Account info serializer."""
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

        if current_user.username != gl_extern_uid:
            raise KeycloakGitLabMismatchError(
                gl_user_id, gl_extern_uid, current_user.id, current_user.username
            )

        # Continue with the rest of the account info serializer chain.
        return original_serializer(remote, resp, user_info, **kwargs)

    return inner
