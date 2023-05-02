"""OIDC settings."""

from invenio_userprofiles.forms import confirm_register_form_preferences_factory
from flask import current_app
from werkzeug.local import LocalProxy

_security = LocalProxy(lambda: current_app.extensions["security"])


def confirm_registration_form(*args, **kwargs):
    Form = confirm_register_form_preferences_factory(_security.confirm_register_form)
    class _Form(Form):
        password = None
        recaptcha = None
        submit = None  # defined in the template
    return _Form(*args, **kwargs)


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
                "visibility": "restricted",
                "email_visibility": "restricted",
            },
        },
        "external_id": cern_upn,
        "external_method": remote.name,
    }

