# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Harvester Reports administration views."""

from flask import current_app, request
from flask_principal import Permission, RoleNeed
from invenio_administration.views.base import AdminResourceListView
from invenio_i18n import lazy_gettext as _
from functools import partial
from invenio_search_ui.searchconfig import search_app_config
import json
from invenio_jobs.models import Job
from invenio_jobs.models import Run

class HarvesterReportsView(AdminResourceListView):
    """Harvester reports admin view for curators."""

    api_endpoint = "/audit-logs/"
    extension_name = "invenio-audit-logs"
    name = "harvester-reports"
    resource_config = "audit_log_resource"

    title = "Harvester Reports"
    menu_label = "Harvester Reports"
    category = "Logs"
    pid_path = "id"
    icon = "file alternate"
    template = "cds_rdm/administration/harvester_reports.html"
    order = 2
    search_request_headers = {"Accept": "application/vnd.inveniordm.v1+json"}

    display_search = True
    display_delete = False
    display_create = False
    display_edit = False

    item_field_list = {
        "resource.type": {"text": _("Resource"), "order": 1, "width": 2},
        "resource.id": {"text": _("Resource ID"), "order": 2},
        "action": {"text": _("Action"), "order": 3},
        "user.id": {"text": _("User"), "order": 4},
        "created": {"text": _("Created"), "order": 5},
    }

    actions = {
        "view_log": {"text": _("View Log"), "payload_schema": None, "order": 1},
        "view_changes": {
            "text": _("View Changes"),
            "payload_schema": None,
            "order": 2,
            "show_for": ["record.publish"],
        },
    }

    search_config_name = "AUDIT_LOGS_SEARCH"
    search_facets_config_name = "AUDIT_LOGS_FACETS"
    search_sort_config_name = "AUDIT_LOGS_SORT_OPTIONS"

    decorators = [
        Permission(RoleNeed("harvester-curator")).require(http_exception=403)
    ]

    @staticmethod
    def disabled():
        """Disable the view on demand."""
        return not current_app.config.get("HARVESTER_REPORTS_ENABLED", True)

    @staticmethod
    def visible_when():
        """Return a callable to check if menu should be visible."""
        return lambda: Permission(RoleNeed("harvester-curator")).can()

    def _get_inspire_job_id(self):
        """Get the INSPIRE harvester job ID."""
        job = Job.query.filter_by(task="process_inspire").first()
        return job.id if job else None

    def _fetch_recent_runs(self, job_id, limit=20):
        """Fetch recent parent runs for the INSPIRE job."""
        # Fetch only parent runs (parent_run_id is None) that have started
        runs = (
            Run.query.filter_by(job_id=job_id, parent_run_id=None)
            .filter(Run.started_at.isnot(None))
            .order_by(Run.started_at.desc())
            .limit(limit)
            .all()
        )

        # Serialize runs with all available info
        return [
            {
                "id": str(run.id),
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                "status": run.status.value if run.status else None,
                "title": run.title or f"Run {run.id}",
                "message": run.message,
            }
            for run in runs
        ]

    def get_context(self, **kwargs):
        """Add runs data to template context."""
        context = super().get_context(**kwargs)

        # Get INSPIRE job and its runs
        job_id = self._get_inspire_job_id()
        if job_id:
            runs = self._fetch_recent_runs(job_id, limit=20)
            context["harvester_runs"] = json.dumps(runs)
            context["default_run"] = json.dumps(runs[0]) if runs else None
        else:
            context["harvester_runs"] = json.dumps([])
            context["default_run"] = None

        return context

    def init_search_config(self, **kwargs):
        """Build search view config."""
        return partial(
            search_app_config,
            config_name=self.get_search_app_name(**kwargs),
            available_facets=current_app.config.get(self.search_facets_config_name),
            sort_options=current_app.config[self.search_sort_config_name],
            endpoint=self.get_api_endpoint(**kwargs),
            headers=self.get_search_request_headers(**kwargs),
            pagination_options=(20, 50),
            default_size=20,
        )