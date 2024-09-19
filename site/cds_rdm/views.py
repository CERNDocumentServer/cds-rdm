# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2023-2024 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Additional views."""

from flask import Blueprint, redirect
from invenio_rdm_records.resources.urls import record_url_for

from cds_rdm.resolver import get_pid_by_legacy_recid


def legacy_redirect(id):
    """Redirect legacy recid."""
    pid = get_pid_by_legacy_recid(id)
    url_path = record_url_for(pid_value=pid)
    return redirect(url_path)


#
# Registration
#
def create_blueprint(app):
    """Register blueprint routes on app."""
    blueprint = Blueprint(
        "cds_rdm",
        __name__,
        template_folder="./templates",
    )
    blueprint.add_url_rule(
        "/legacy/<id>",
        view_func=legacy_redirect,
        strict_slashes=False,
    )

    # Add URL rules
    return blueprint
