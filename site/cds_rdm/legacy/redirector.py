# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2023-2024 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Redirector functions and rules."""

from flask import Blueprint, current_app, redirect, render_template, request, url_for
from invenio_base import invenio_url_for
from invenio_communities.views.ui import not_found_error
from sqlalchemy.orm.exc import NoResultFound

from .errors import VersionNotFound
from .resolver import get_pid_by_legacy_recid, get_record_by_version

HTTP_MOVED_PERMANENTLY = 301


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


def legacy_record_redirect(legacy_id):
    """Redirect legacy recid."""
    pid = get_pid_by_legacy_recid(legacy_id)
    url_path = invenio_url_for(
        "invenio_app_rdm_records.record_detail", pid_value=pid.pid_value
    )
    return redirect(url_path, HTTP_MOVED_PERMANENTLY)


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
    return redirect(url_path, HTTP_MOVED_PERMANENTLY)


# Redirection are implemented in CDS LBs, also because some collections map to searches and not
# to communities.
# def legacy_collection_redirect(collection_name):
#     """Redirection for legacy collections."""
#     cds_community_uuid = current_app.config["CDS_REDIRECTION_COLLECTIONS_MAPPING"].get(
#         collection_name, None
#     )
#     if not cds_community_uuid:
#         raise NoResultFound
#     url_path = url_for(
#         "invenio_app_rdm_communities.communities_home",
#         pid_value=cds_community_uuid,
#         **request.args,
#     )
#     return redirect(url_path, HTTP_MOVED_PERMANENTLY)


# Redirection are implemented in CDS LBs
# def legacy_search_redirect():
#     """
#     Redirection for legacy search. Transforms the legacy URL syntax into RDM URL syntax.

#         /legacy/search?cc=<legacy collection name>... -> /communities/<rdm_community_id>/records?...
#         /legacy/search?c=<legacy collection name>... -> /communities/<rdm_community_id>/records?...
#         /legacy/search?c=<legacy collection name>&p=<query>... -> /communities/<rdm_community_id>/records?q=<query>...
#     """
#     query_params = {"q": request.args.get("p")}  # `p` in legacy is the search query
#     # Fetch current collection if it exists
#     collection_name = request.args.get("cc", None)
#     # If not, then fetch from collection list (query param 'c')
#     if not collection_name:
#         collections_list = request.args.getlist("c")
#         collection_name = collections_list[0] if collections_list else None
#     # If collection not found, i.e. 'c' or 'cc' not found, redirect to global record search with search query
#     if not collection_name:
#         url = url_for(
#             "invenio_search_ui.search",
#             **query_params,
#         )
#     else:
#         url = url_for(
#             "cds_rdm.legacy_collection_redirect",
#             collection_name=collection_name,
#             **query_params,
#         )
#     return redirect(url, HTTP_MOVED_PERMANENTLY)


#
# Registration
#
def create_blueprint(app):
    """Register blueprint routes on app."""
    blueprint = Blueprint(
        "cds_rdm", __name__, template_folder="../templates", url_prefix="/legacy"
    )
    # blueprint.add_url_rule(
    #     "/search",
    #     view_func=legacy_search_redirect,
    #     strict_slashes=False,
    # )
    blueprint.add_url_rule(
        "/record/<legacy_id>",
        view_func=legacy_record_redirect,
        strict_slashes=False,
    )
    blueprint.add_url_rule(
        "/record/<legacy_id>/files/<path:filename>",
        view_func=legacy_files_redirect,
        strict_slashes=False,
    )
    blueprint.add_url_rule(
        "/record/<legacy_id>/files/",
        view_func=legacy_record_redirect,
        strict_slashes=False,
    )
    # blueprint.add_url_rule(
    #     "/collection/<collection_name>",
    #     view_func=legacy_collection_redirect,
    #     strict_slashes=False,
    # )
    blueprint.register_error_handler(NoResultFound, not_found_error)
    blueprint.register_error_handler(VersionNotFound, version_not_found_error)

    # Add URL rules
    return blueprint
