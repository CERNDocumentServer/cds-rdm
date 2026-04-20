# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Harvester download resource."""

import re
import uuid
from datetime import datetime

from flask import Response, current_app, request
from flask_resources import Resource, route
from invenio_access.permissions import system_identity
from invenio_jobs.models import Run
from invenio_jobs.proxies import current_jobs_logs_service

from cds_rdm.administration.permissions import curators_permission

INSPIRE_HARVESTER_TASK = "process_inspire"


class HarvesterDownloadResource(Resource):
    """Harvester download resource."""

    def create_url_rules(self):
        """Create the URL rules for the download resource."""
        routes = self.config.routes
        return [
            route("GET", routes["download"], self.download),
        ]

    def download(self):
        """Download a harvester run's logs as a plain-text ``.log`` file.

        Mirrors the admin job-run page: status header, failure banner,
        truncation warning, and task-grouped entries formatted as
        ``[yyyy-MM-dd HH:mm] LEVEL message``.
        """
        permission = curators_permission
        if not permission.can():
            return {"message": "Permission denied"}, 403

        run_id = request.args.get("run_id", "").strip()
        if not run_id:
            return {"message": "Missing run_id"}, 400
        try:
            uuid.UUID(run_id)
        except ValueError:
            return {"message": "Invalid run_id"}, 400

        run = Run.query.filter_by(id=run_id, parent_run_id=None).one_or_none()
        if not run:
            return {"message": "Run not found"}, 404

        if not run.job or run.job.task != INSPIRE_HARVESTER_TASK:
            return {"message": "Run is not a harvester run"}, 404


        max_results = current_app.config.get("JOBS_LOGS_MAX_RESULTS", 2000)
        try:
            result = current_jobs_logs_service.search(
                system_identity,
                params={"q": str(run.id), "sort": "timestamp"},
            )
            hits = list(result.hits)
            total = result.total or len(hits)
        except Exception:
            current_app.logger.exception(
                "Failed to fetch structured job logs for harvester run %s", run.id
            )
            hits = []
            total = 0

        def _format_timestamp(raw):
            # Admin UI (RunsLogs.js) format.
            if not raw:
                return "N/A"
            try:
                return datetime.fromisoformat(
                    raw.replace("Z", "+00:00")
                ).strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                return raw

        # Group by context.task_id in first-seen order (RunsLogs.js buildLogTree).
        task_groups = {}
        seen = set()
        error_count = 0
        warning_count = 0
        for hit in hits:
            raw_ts = hit.get("timestamp")
            level = hit.get("level", "INFO")
            # Collapse whitespace so multi-line errors render on one line
            # (admin UI does the same via ``white-space: normal``).
            message = re.sub(r"\s+", " ", (hit.get("message") or "")).strip()
            key = (raw_ts, level, message)
            if key in seen:
                continue
            seen.add(key)
            if level == "ERROR":
                error_count += 1
            elif level == "WARNING":
                warning_count += 1
            task_id = (hit.get("context") or {}).get("task_id") or "unknown"
            task_groups.setdefault(task_id, []).append(
                f"[{_format_timestamp(raw_ts)}] {level} {message}"
            )

        lines = [line for group in task_groups.values() for line in group]

        header = []
        status = getattr(run.status, "name", str(run.status))
        header.append(f"Status: {status}")
        header.append(f"Started: {_format_timestamp(run.started_at.isoformat())}")
        if run.finished_at:
            header.append(
                f"Finished: {_format_timestamp(run.finished_at.isoformat())}"
            )

        summary = []
        if status in ("FAILED", "PARTIAL_SUCCESS", "SUCCESS"):
            summary.append(
                {
                    "FAILED": "Job failed",
                    "PARTIAL_SUCCESS": "Job partially succeeded",
                    "SUCCESS": "Job completed successfully",
                }[status]
            )
        if run.message:
            summary.append(run.message)
        if error_count:
            summary.append(f"{error_count} error(s) found in logs below")
        if warning_count:
            summary.append(f"{warning_count} warning(s) found in logs below")
        if summary:
            header.append("")
            header.extend(summary)

        if total and total > len(lines):
            header.append(
                f"Showing first {len(lines)} of {total} log entries "
                f"(truncated at JOBS_LOGS_MAX_RESULTS={max_results})."
            )
        header.append("=" * 80)

        logs = "\n".join(header + lines)

        if not lines:
            logs += "\n" + (run.message or "No logs available for this run.\n")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"harvester_logs_{run.id}_{timestamp}.log"

        return Response(
            logs,
            mimetype="text/plain",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
