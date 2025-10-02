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
