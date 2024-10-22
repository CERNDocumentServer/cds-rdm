# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2023-2024 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Additional views."""

from flask import Blueprint, current_app, redirect, render_template, request, url_for
from invenio_rdm_records.resources.urls import record_url_for
from sqlalchemy.orm.exc import NoResultFound

from cds_rdm.resolver import get_pid_by_legacy_recid


def not_found_error(error):
    """Handler for 'Not Found' errors."""
    return render_template(current_app.config["THEME_404_TEMPLATE"]), 404


def legacy_redirect(
    legacy_id,
    filename=None,
):
    """Redirect legacy recid."""
    pid = get_pid_by_legacy_recid(legacy_id)
    if filename:
        url_path = url_for(
            "invenio_app_rdm_records.record_file_preview",
            pid_value=pid,
            filename=filename,
            **request.args,  # Transform if required
        )
    else:
        url_path = record_url_for(pid_value=pid)
    current_app.logger.debug(url_path)
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
        "/record/<legacy_id>",
        view_func=legacy_redirect,
        strict_slashes=False,
    )
    blueprint.add_url_rule(
        "/record/<legacy_id>/files/<path:filename>",
        view_func=legacy_redirect,
        strict_slashes=False,
    )
    blueprint.add_url_rule(
        "/record/<legacy_id>/files/",
        view_func=legacy_redirect,
        strict_slashes=False,
    )
    blueprint.register_error_handler(NoResultFound, not_found_error)

    # Add URL rules
    return blueprint
