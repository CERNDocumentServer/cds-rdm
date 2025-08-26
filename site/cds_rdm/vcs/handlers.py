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
    def inner(remote, resp, user_info, **kwargs):
        cern_client_id = current_oauthclient.oauth.remote_apps.get(
            cern_remote_app_name
        ).consumer_key

        user_keycloak_id: str | None = None
        for remote_account in current_user.remote_accounts:
            if remote_account.client_id == cern_client_id:
                user_keycloak_id = remote_account.extra_data.get("keycloak_id")

        if user_keycloak_id is None:
            raise KeycloakIdentityNotFoundError(current_user.id)

        gl_user_id = str(user_info["id"])
        gl_identities = user_info["identities"]
        gl_extern_uid: str | None = None
        for identity in gl_identities:
            if identity["provider"] != "openid_connect":
                continue

            gl_extern_uid = identity["extern_uid"]

        if gl_extern_uid is None:
            raise GitLabIdentityNotFoundError(gl_user_id)

        if user_keycloak_id != gl_extern_uid:
            raise KeycloakGitLabMismatchError(
                gl_user_id, gl_extern_uid, current_user.id, user_keycloak_id
            )

        return original_serializer(remote, resp, user_info, **kwargs)

    return inner
