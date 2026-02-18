# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2024 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""CDS views."""

from flask import Blueprint, current_app, render_template, url_for
from flask_principal import AnonymousIdentity
from invenio_access.permissions import any_user
from invenio_app_rdm.records_ui.utils import dump_external_resource
from invenio_communities import current_communities
from invenio_i18n import _

from .schemes import legacy_cds_pattern

blueprint = Blueprint("cds-rdm_ext", __name__)


def frontpage_view_function():
    """Frontpage."""
    anonymous_identity = AnonymousIdentity()
    anonymous_identity.provides.add(any_user)
    featured_communities_search = current_communities.service.featured_search(
        anonymous_identity
    )

    featured = featured_communities_search.to_dict()["hits"]["hits"]
    context = {"featured_communities": featured}

    return render_template(
        current_app.config["THEME_FRONTPAGE_TEMPLATE"],
        show_intro_section=current_app.config["THEME_SHOW_FRONTPAGE_INTRO_SECTION"],
        **context,
    )


def create_cds_clc_sync_bp(app):
    """Create records blueprint."""
    ext = app.extensions["cds-rdm"]
    return ext.clc_sync_resource.as_blueprint()


def create_harvester_download_bp(app):
    """Create harvester download blueprint."""
    ext = app.extensions["cds-rdm"]
    return ext.harvester_download_resource.as_blueprint()


def inspire_link_render(record):
    """Entry for INSPIRE."""
    ret = []
    inspire_rel_ids = [
        rel_id["identifier"]
        for rel_id in record.data["metadata"].get("related_identifiers", [])
        if rel_id["scheme"] == "inspire"
    ]
    for rel_value in inspire_rel_ids:
        ret.append(
            dump_external_resource(
                f"https://inspirehep.net/literature/{rel_value}",
                title="INSPIRE",
                section=_("Indexed in"),
                icon=url_for("static", filename="images/inspire_logo.png"),
            )
        )
    return ret


def get_linked_records_search_query(record):
    """Build search query for linked records.

    Returns a search query string to find:
    1. Records that this record references in related_identifiers (scheme="cds")
       - For legacy numeric recids: searches both id and metadata.identifiers
       - For new alphanumeric PIDs: searches only id
    2. Records that reference this record in their related_identifiers (scheme="cds")

    This handles CDS migration where old numeric recids are stored in
    metadata.identifiers.identifier when records get new PIDs.
    """
    # Get CDS identifiers from related_identifiers
    related_identifiers = record.data["metadata"].get("related_identifiers", [])
    cds_related_ids = [
        rel_id.get("identifier")
        for rel_id in related_identifiers
        if rel_id.get("scheme") == "cds" and rel_id.get("identifier")
    ]

    # Build query parts
    query_parts = []

    # Part 1: Records that this record references (forward)
    # Search by record id using the CDS identifier
    for cds_id in cds_related_ids:
        if legacy_cds_pattern.match(cds_id):
            # Old numeric recid: Search both by id AND in metadata.identifiers
            # This handles both non-migrated records (where id = recid)
            # and migrated records (where recid is stored in identifiers)
            # Must filter by scheme:cds to avoid matching other identifier types
            query_parts.append(
                f'(id:"{cds_id}" OR '
                f'(metadata.identifiers.scheme:cds AND metadata.identifiers.identifier:"{cds_id}"))'
            )
        else:
            # New alphanumeric PID: Search only by id (current behavior)
            query_parts.append(f'id:"{cds_id}"')

    # Part 2: Records that reference this record (reverse)
    # Find records that have this record's CDS PIDs in their related_identifiers
    record_id = record.data.get("id")
    query_parts.append(
        "(metadata.related_identifiers.scheme:cds AND "
        f'metadata.related_identifiers.identifier:"{record_id}")'
    )

    if not query_parts:
        return None

    # Combine all query parts with OR
    combined_query = (
        " OR ".join(query_parts) if len(query_parts) > 1 else query_parts[0]
    )

    # Exclude the current record and only show published records
    final_query = f'({combined_query}) AND is_published:true AND NOT id:"{record_id}"'

    return final_query


