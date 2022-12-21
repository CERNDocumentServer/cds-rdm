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


def cern_info_serializer(remote, resp, user_info):
    return {
        "user": {
            "active": True,
            "email": user_info["email"],
            "profile": {
                "full_name": user_info["name"],
                "username": user_info["preferred_username"],
            },
            "prefs": {
                "visibility": "restricted",
                "email_visibility": "restricted",
            },
        },
        "external_id": user_info["cern_upn"],
        "external_method": remote.name,
    }
