"""OIDC settings."""

from invenio_db import db
from invenio_userprofiles.forms import confirm_register_form_preferences_factory
from flask import current_app
from werkzeug.local import LocalProxy
from invenio_oauthclient import current_oauthclient
from invenio_oauthclient.contrib.keycloak.handlers import get_user_info
from invenio_oauthclient.utils import oauth_link_external_id

_security = LocalProxy(lambda: current_app.extensions["security"])


def confirm_registration_form(*args, **kwargs):
    Form = confirm_register_form_preferences_factory(_security.confirm_register_form)

    class _Form(Form):
        password = None
        recaptcha = None
        submit = None  # defined in the template

    return _Form(*args, **kwargs)


def cern_group_serializer(remote, groups, **kwargs):
    """Serialize the groups response object."""
    serialized_groups = []
    # E-groups do have unique names and this name cannot be updated, therefore the name can act as an ID for invenio
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


def cern_group_handler(remote, resp):
    """Retrieves groups from remote account."""
    token_user_info, user_info = get_user_info(remote, resp)
    groups = token_user_info.get("groups", [])
    handlers = current_oauthclient.signup_handlers[remote.name]
    # `remote` param automatically injected via `make_handler` helper
    return handlers["groups_serializer"](groups)


def cern_info_serializer(remote, resp, token_user_info, user_info):
    user_info = user_info or {}  # prevent errors when accessing None.get(...)

    email = token_user_info.get("email") or user_info["email"]
    full_name = token_user_info.get("name") or user_info.get("name")
    username = token_user_info.get("preferred_username") or user_info.get(
        "preferred_username"
    )
    cern_upn = token_user_info.get("cern_upn") or user_info.get("cern_upn")
    return {
        "user": {
            "active": True,
            "email": email,
            "profile": {
                "full_name": full_name,
                "username": username,
            },
            "prefs": {
                "visibility": "public",
                "email_visibility": "restricted",
                "locale": "en",
            },
        },
        "external_id": cern_upn,
        "external_method": remote.name,
    }
