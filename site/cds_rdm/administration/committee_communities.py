# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Administration views for committee approval communities."""

from flask import request
from invenio_administration.views.base import (
    AdminResourceCreateView,
    AdminResourceDetailView,
    AdminResourceEditView,
    AdminResourceListView,
)
from invenio_communities.communities.records.models import CommunityMetadata
from invenio_i18n import lazy_gettext as _

from cds_rdm.committee_communities.models import CommitteeApprovalCommunity


def _community_options(include=None):
    """Return dropdown options for communities not yet enrolled.

    ``include`` is the id of a community to list even though it is enrolled
    (the one being edited).

    The option text includes slug, title and UUID so the search box matches
    on any of them.
    """
    enrolled = {entry.community_id for entry in CommitteeApprovalCommunity.get_all()}
    options = []
    for community in CommunityMetadata.query.order_by(CommunityMetadata.slug):
        if str(community.id) != include and (
            community.id in enrolled or community.is_deleted
        ):
            continue
        title = (community.json or {}).get("metadata", {}).get("title", "")
        options.append(
            {
                "id": str(community.id),
                "title_l10n": f"{community.slug} — {title} ({community.id})",
            }
        )
    return options


class CommitteeCommunityAdminMixin:
    """Common admin properties."""

    api_endpoint = "/committee-communities"
    resource_config = "committee_communities_resource"
    pid_path = "id"
    # Access is restricted to ``administration-access`` (the base class default).


_form_fields = {
    "community_id": {
        "order": 1,
        "text": _("Community ID"),
        "description": _(
            "UUID of the community to enrol in the approval workflow "
            "(not the slug, as slugs can be renamed)."
        ),
    },
    "label": {
        "order": 2,
        "text": _("Label"),
        "description": _("Shown in request buttons/headings, e.g. 'EP approval'."),
    },
    "committee_name": {
        "order": 3,
        "text": _("Committee name"),
        "description": _("Shown in review-step labels/text, e.g. 'EP Board'."),
    },
    "referee_group": {
        "order": 4,
        "text": _("Referee group"),
        "description": _(
            "Id of the group whose members act as referees, i.e. the CERN "
            "e-group name. Must be an existing group."
        ),
    },
    "read_only": {
        "order": 5,
        "text": _("Read only"),
        "description": _("Only allow read-only access to the workflow."),
    },
    "report_number_prefix": {
        "order": 6,
        "text": _("Report number prefix"),
        "description": _("Fixed prefix, e.g. 'CERN-EP'."),
    },
    "report_number_include_year": {
        "order": 7,
        "text": _("Include year"),
        "description": _("Append the current year after the prefix."),
    },
    "report_number_counter_digits": {
        "order": 8,
        "text": _("Counter digits"),
        "description": _("Zero-padding width of the counter, e.g. 3 gives '001'."),
    },
}


class CommitteeCommunityListView(CommitteeCommunityAdminMixin, AdminResourceListView):
    """List view."""

    name = "committee-communities"
    title = _("Committee approval")
    menu_label = _("Committee approval")
    category = _("Communities")
    icon = "check circle"
    search_request_headers = {"Accept": "application/vnd.inveniordm.v1+json"}

    display_search = True
    display_create = True
    display_edit = True
    display_delete = True

    create_view_name = "committee-community-create"

    search_config_name = "COMMITTEE_COMMUNITIES_SEARCH"
    search_facets_config_name = "COMMITTEE_COMMUNITIES_FACETS"
    search_sort_config_name = "COMMITTEE_COMMUNITIES_SORT_OPTIONS"

    item_field_list = {
        "community_title": {"text": _("Community"), "order": 1, "width": 3},
        "community_slug": {"text": _("Slug"), "order": 2, "width": 2},
        "label": {"text": _("Label"), "order": 3, "width": 2},
        "committee_name": {"text": _("Committee"), "order": 4, "width": 2},
        "referee_group_name": {"text": _("Referee group"), "order": 5, "width": 3},
        "report_number_prefix": {"text": _("Prefix"), "order": 6, "width": 2},
        "read_only": {"text": _("Read only"), "order": 7, "width": 1},
    }


class CommitteeCommunityCreateView(
    CommitteeCommunityAdminMixin, AdminResourceCreateView
):
    """Create view."""

    name = "committee-community-create"
    url = "/committee-communities/create"
    title = _("Enrol community in committee approval")
    list_view_name = "committee-communities"

    @property
    def form_fields(self):
        """Form fields, with the community picker populated at request time."""
        return {
            **_form_fields,
            "community_id": {
                **_form_fields["community_id"],
                "text": _("Community"),
                "description": _(
                    "Search by slug, title or UUID. Communities that are already "
                    "enrolled are not listed."
                ),
                "options": _community_options(),
                "search": True,
                "placeholder": _("Select a community"),
            },
        }


class CommitteeCommunityEditView(CommitteeCommunityAdminMixin, AdminResourceEditView):
    """Edit view."""

    name = "committee-community-edit"
    url = "/committee-communities/<pid_value>/edit"
    title = _("Edit committee approval community")
    list_view_name = "committee-communities"

    @property
    def form_fields(self):
        """Form fields, with the (read-only) community picker for this entry."""
        entry = CommitteeApprovalCommunity.get_by_id(
            (request.view_args or {}).get("pid_value")
        )
        current = str(entry.community_id) if entry else None
        return {
            **_form_fields,
            "community_id": {
                **_form_fields["community_id"],
                "text": _("Community"),
                "description": _("The enrolled community cannot be changed."),
                "options": _community_options(include=current),
                "search": True,
            },
            "created": {"order": 9},
            "updated": {"order": 10},
        }


class CommitteeCommunityDetailView(
    CommitteeCommunityAdminMixin, AdminResourceDetailView
):
    """Detail view."""

    name = "committee-community-details"
    url = "/committee-communities/<pid_value>"
    title = _("Committee approval community")
    list_view_name = "committee-communities"
    display_edit = True
    display_delete = True
    request_headers = {"Accept": "application/vnd.inveniordm.v1+json"}

    item_field_list = {
        "community_id": {"text": _("Community ID"), "order": 1},
        "community_title": {"text": _("Community"), "order": 2},
        "community_slug": {"text": _("Slug"), "order": 3},
        "label": {"text": _("Label"), "order": 4},
        "committee_name": {"text": _("Committee name"), "order": 5},
        "referee_group_name": {"text": _("Referee group"), "order": 6},
        "read_only": {"text": _("Read only"), "order": 7},
        "report_number_prefix": {"text": _("Report number prefix"), "order": 8},
        "report_number_include_year": {"text": _("Include year"), "order": 9},
        "report_number_counter_digits": {"text": _("Counter digits"), "order": 10},
        "created": {"text": _("Created"), "order": 11},
        "updated": {"text": _("Updated"), "order": 12},
    }
