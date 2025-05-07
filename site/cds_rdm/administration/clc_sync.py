# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 CERN.
#
# Invenio-Jobs is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Invenio administration view module."""

from flask import current_app
from invenio_administration.views.base import (
    AdminResourceDetailView,
    AdminResourceListView,
)
from invenio_i18n import lazy_gettext as _
from invenio_jobs.config import JOBS_QUEUES
from invenio_jobs.models import Task
from invenio_jobs.services.schema import RunSchema
from invenio_jobs.services.ui_schema import ScheduleUISchema


class CLCSyncAdminMixin:
    """Common admin properties."""

    api_endpoint = "/clc"
    resource_config = "clc_sync_resource"
    pid_path = "id"

    display_search = True
    display_delete = False
    display_create = False
    display_edit = False

    search_config_name = "CLC_SYNC_SEARCH"
    search_sort_config_name = "CLC_SYNC_SORT_OPTIONS"
    search_facets_config_name = "CLC_SYNC_FACETS"

    actions = {}


class CLCSyncListView(CLCSyncAdminMixin, AdminResourceListView):
    """Configuration for CLC sync list view."""

    name = "clc"
    search_request_headers = {"Accept": "application/vnd.inveniordm.v1+json"}
    title = "CLC Sync"
    menu_label = "CLC Sync"
    category = "Site management"
    icon = "sync"

    item_field_list = {
        "created": {"text": _("Created"), "order": 1, "width": 4},
        "clc_record_pid": {"text": _("CLC record"), "order": 2, "width": 2},
        "parent_record_pid": {"text": _("CDS record"), "order": 3, "width": 2},
        "status": {"text": _("Status"), "order": 4, "width": 2},
        "message": {"text": _("Message"), "order": 4, "width": 3},
        "auto_sync": {"text": _("Auto sync"), "order": 5, "width": 1},
    }


class CLCSyncDetailView(CLCSyncAdminMixin, AdminResourceDetailView):
    """Admin banner detail view."""

    url = "/clc/<pid_value>"
    name = "clc-sync-details"
    title = "CLC Sync Details"

    list_view_name = "clc"
    pid_path = "id"

    item_field_list = {
        "created": {"text": _("Created"), "order": 1},
        "clc_record_pid": {"text": _("CLC record"), "order": 2},
        "parent_record_pid": {"text": _("CDS record"), "order": 3},
        "status": {"text": _("Status"), "order": 4},
        "message": {"text": _("Message"), "order": 5},
        "last_sync": {"text": _("Last sync"), "order": 5},
        "auto_sync": {"text": _("Auto sync"), "order": 6},
    }
