# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Helpers for INSPIRE harvester run logs."""

import re
import uuid
from datetime import datetime

from flask import current_app
from flask_babel import format_datetime
from invenio_access.permissions import system_identity
from invenio_i18n import gettext as _
from invenio_jobs.models import Run
from invenio_jobs.proxies import current_jobs_logs_service

INSPIRE_HARVESTER_TASK = "process_inspire"


class HarvesterRunError(Exception):
    """Error raised when a requested harvester run cannot be used."""

    def __init__(self, message, code):
        """Constructor."""
        self.message = message
        self.code = code
        super().__init__(message)


def format_timestamp(value):
    """Format timestamps for display."""
    if value is None or value == "":
        return "N/A"
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return str(value)
    return format_datetime(dt, "yyyy-MM-dd HH:mm")


def resolve_harvester_run(run_id):
    """Return a top-level INSPIRE harvester run or raise ``HarvesterRunError``."""
    run_id = (run_id or "").strip()
    if not run_id:
        raise HarvesterRunError("Missing run_id", 400)
    try:
        uuid.UUID(run_id)
    except ValueError:
        raise HarvesterRunError("Invalid run_id", 400)

    run = Run.query.filter_by(id=run_id, parent_run_id=None).one_or_none()
    if not run:
        raise HarvesterRunError("Run not found", 404)
    if not run.job or run.job.task != INSPIRE_HARVESTER_TASK:
        raise HarvesterRunError("Run is not a harvester run", 404)
    return run


def fetch_harvester_run_logs(run):
    """Return ``(hits, total)`` from structured job logs."""
    try:
        result = current_jobs_logs_service.search(
            system_identity,
            params={
                "q": f'"{run.id}"',
                "sort": "timestamp",
            },
        )
        hits = list(result.hits)
        total = result.total or len(hits)
    except Exception:
        current_app.logger.exception(
            "Failed to fetch structured job logs for harvester run %s", run.id
        )
        hits = []
        total = 0
    return hits, total


def lines_from_hits(hits):
    """Return de-duplicated log lines and severity counts."""
    task_groups = {}
    seen = set()
    error_count = 0
    warning_count = 0
    for hit in hits:
        raw_ts = hit.get("timestamp")
        level = hit.get("level", "INFO")
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
            f"[{format_timestamp(raw_ts)}] {level} {message}"
        )
    lines = [line for group in task_groups.values() for line in group]
    return lines, error_count, warning_count


def plain_text_log(run, lines, total, error_count, warning_count):
    """Build the plain-text log file content."""
    max_results = current_app.config.get("JOBS_LOGS_MAX_RESULTS", 2000)
    status = getattr(run.status, "name", str(run.status))
    header = [
        f"Status: {status}",
        f"Started: {format_timestamp(run.started_at)}",
    ]
    if run.finished_at:
        header.append(f"Finished: {format_timestamp(run.finished_at)}")

    summary = []
    if status in ("FAILED", "PARTIAL_SUCCESS", "SUCCESS"):
        summary.append(
            {
                "FAILED": _("Job failed"),
                "PARTIAL_SUCCESS": _("Job partially succeeded"),
                "SUCCESS": _("Job completed successfully"),
            }[status]
        )
    if run.message:
        summary.append(run.message)
    if error_count:
        summary.append(_("%(count)s error(s) found in logs below", count=error_count))
    if warning_count:
        summary.append(
            _("%(count)s warning(s) found in logs below", count=warning_count)
        )
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
    return logs


def report_context(run_id):
    """Build context for the colored HTML report page."""
    run = resolve_harvester_run(run_id)
    hits, total = fetch_harvester_run_logs(run)
    lines, error_count, _unused_warnings = lines_from_hits(hits)
    status = getattr(run.status, "name", str(run.status))

    truncation_message = None
    if total and total > len(lines):
        truncation_message = (
            f"Log results truncated. Too many log results returned ({total}). "
            f"Only the most recent {len(lines)} results are shown."
        )

    display_title = (getattr(run, "title", None) or "").strip() or f"Run {run.id}"
    return {
        "run": run,
        "title": display_title,
        "status": status,
        "started_at": format_timestamp(run.started_at),
        "finished_at": format_timestamp(run.finished_at) if run.finished_at else None,
        "truncation_message": truncation_message,
        "lines": lines,
        "error_count": error_count,
    }
