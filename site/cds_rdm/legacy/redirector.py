# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2023-2024 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Redirector functions and rules."""

from flask import Blueprint, current_app, redirect, render_template, request, url_for
from invenio_rdm_records.resources.urls import record_url_for
from sqlalchemy.orm.exc import NoResultFound

from .errors import VersionNotFound
from .resolver import get_pid_by_legacy_recid, get_record_by_version


def not_found_error(error):
    """Handler for 'Not Found' errors."""
    return render_template(current_app.config["THEME_404_TEMPLATE"]), 404


def version_not_found_error(error):
    """Handler for record version not found errors."""
    return (
        render_template(
            "cds_rdm/version_not_found.html",
            version=error.version,
            latest_record=error.latest_record,
        ),
        404,
    )


def legacy_redirect(legacy_id):
    """Redirect legacy recid."""
    pid = get_pid_by_legacy_recid(legacy_id)
    url_path = record_url_for(pid_value=pid.pid_value)
    return redirect(url_path)


def legacy_files_redirect(legacy_id, filename):
    """Redirection for legacy files."""
    parent_pid = get_pid_by_legacy_recid(legacy_id)
    query_params = request.args.copy()
    version = query_params.pop("version", None)
    record = get_record_by_version(parent_pid.pid_value, version)
    # Directly download files from redirected link to replicate the `allfiles-` behaviour from legacy
    if filename.startswith("allfiles-"):
        url_path = record["links"]["archive"]
    else:
        url_path = url_for(
            "invenio_app_rdm_records.record_file_preview",
            pid_value=record["id"],
            filename=filename,
            **query_params,
        )
    return redirect(url_path)


#
# Registration
#
def create_blueprint(app):
    """Register blueprint routes on app."""
    blueprint = Blueprint(
        "cds_rdm",
        __name__,
        template_folder="../templates",
    )
    blueprint.add_url_rule(
        "/record/<legacy_id>",
        view_func=legacy_redirect,
        strict_slashes=False,
    )
    blueprint.add_url_rule(
        "/record/<legacy_id>/files/<path:filename>",
        view_func=legacy_files_redirect,
        strict_slashes=False,
    )
    blueprint.add_url_rule(
        "/record/<legacy_id>/files/",
        view_func=legacy_redirect,
        strict_slashes=False,
    )
    blueprint.register_error_handler(NoResultFound, not_found_error)
    blueprint.register_error_handler(VersionNotFound, version_not_found_error)

    # Add URL rules
    return blueprint
