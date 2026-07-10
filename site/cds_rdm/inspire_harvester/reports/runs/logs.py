# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Helpers for INSPIRE harvester run logs.

Grouping assumes stable messages from writer/transformer mappers. This module
only peels external wrappers (datastream skip logs, logger prefixes) and
collapses a few infra volatiles we do not control (vocab terms, URLs).
"""

import ast
import re
import uuid
from collections import OrderedDict
from datetime import datetime

from flask import current_app
from flask_babel import format_datetime
from invenio_access.permissions import system_identity
from invenio_i18n import gettext as _
from invenio_jobs.models import Run
from invenio_jobs.proxies import current_jobs_logs_service

from cds_rdm.utils import compact_text

INSPIRE_HARVESTER_TASK = "process_inspire"
INSPIRE_LITERATURE_URL = "https://inspirehep.net/literature/"
HARVESTER_RUN_LOGS_MAX_PAGES = 50

_GROUPABLE_LEVELS = frozenset({"ERROR", "WARNING"})
_RECORD_ID_PATTERN = re.compile(r"\[(?:INSPIRE#|inspire_id=)(?P<id>[^\]]+)\]")
_SKIP_SUMMARY_SUFFIX = " transformed entries with errors."
_WRITER_PREFIXES = (
    "Error while processing entry:",
    "Validation error while processing entry:",
)
_VALIDATION_SPLIT = re.compile(r"\bRecord validation failed:\s*", re.IGNORECASE)
_VOCAB_TERM_PATTERN = re.compile(
    r"\bvocabulary term\s+['\"][^'\"]+['\"]\s+not found in\s+['\"]([^'\"]+)['\"]",
    re.IGNORECASE,
)
_URL_PATTERN = re.compile(r"https?://\S+")
_DETAILS_SUFFIX = re.compile(r"\s*\|\s*details:\s*.*$", re.IGNORECASE)
# Defensive: older ERROR lines and debug bleed can append CDS id lists.
_CDS_IDS_SUFFIX = re.compile(r"\s*cds ids?:\s*.*$", re.IGNORECASE)


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
        all_hits = []
        search_after = None
        total = None
        max_pages = current_app.config.get(
            "HARVESTER_RUN_LOGS_MAX_PAGES", HARVESTER_RUN_LOGS_MAX_PAGES
        )
        page_size = current_app.config.get("JOBS_LOGS_MAX_RESULTS", 2000)

        for _ in range(max_pages):
            params = {"q": f'"{run.id}"', "sort": "timestamp"}
            if search_after:
                params["search_after"] = search_after

            result = current_jobs_logs_service.search(system_identity, params=params)
            if total is None:
                total = result.total

            batch = list(result.hits)
            if not batch:
                break

            all_hits.extend(batch)
            if total and len(all_hits) >= total:
                break
            if len(batch) < page_size:
                break

            search_after = result.to_dict().get("hits", {}).get("sort")
            if not search_after:
                break

        return all_hits, total or len(all_hits)
    except Exception:
        current_app.logger.exception(
            "Failed to fetch structured job logs for harvester run %s", run.id
        )
        return [], 0


def _extract_record_id(message):
    """Extract INSPIRE id from log text.

    Examples:
        Input: "[INSPIRE#12345] Multiple records match."
        Output: "12345"

        Input: "Multiple records match."
        Output: None
    """
    match = _RECORD_ID_PATTERN.search(message or "")
    return match.group("id") if match else None


def _skip_log_kind(message):
    """Classify datastream skip logs: ``summary``, ``entry``, or ``None``.

    Examples:
        Input: "Skipping 3 transformed entries with errors."
        Output: "summary"

        Input: "Skipped entry with errors: ['[INSPIRE#1] More than 1 DOI was found.']"
        Output: "entry"

        Input: "[INSPIRE#1] File checksum mismatch."
        Output: None
    """
    text = compact_text(message)
    if text.startswith("Skipping ") and text.endswith(_SKIP_SUMMARY_SUFFIX):
        return "summary"
    if text.startswith("Skipped entry "):
        return "entry"
    return None


def _peel_string_list(text):
    """If ``text`` is a Python list dump of strings, join them.

    Datastream skip logs can serialize ``errors`` as a Python list string.
    This unwraps that representation so grouping sees plain reasons.

    Examples:
        Input: "['[INSPIRE#1601699] Unexpected schema in external_system_identifiers.']"
        Output: "[INSPIRE#1601699] Unexpected schema in external_system_identifiers."

        Input: "['first error', 'second error']"
        Output: "first error | second error"

        Input: "plain message"
        Output: "plain message"
    """
    candidate = text.strip()
    if not (candidate.startswith("[") and candidate.endswith("]")):
        return text
    try:
        parsed = ast.literal_eval(candidate)
    except (ValueError, SyntaxError):
        return text
    if isinstance(parsed, list) and parsed and all(isinstance(x, str) for x in parsed):
        return " | ".join(compact_text(item) for item in parsed)
    return text


def _unwrap_message(message):
    """Build the normalized grouping reason from a raw log message.

    This function now does both steps in one place:
      1) unwrap/strip wrappers and volatile suffixes
      2) normalize the resulting reason for stable bucket titles

    The raw log line is still preserved separately for report drill-down.

    Examples:
        Input:
            "Skipped entry with errors: ['[INSPIRE#2961010] More than 1 DOI was found. | details: doi=10.bad/x']"
        Output:
            "more than 1 doi was found."

        Input:
            "[INSPIRE#333] Error while processing entry: Record validation failed: metadata.title: Required."
        Output:
            "metadata.title: required."

        Input:
            "[INSPIRE#1] Vocabulary term not found in 'experiments'. | details: term=x-062"
        Output:
            "vocabulary term not found in 'experiments'."
    """
    reason = compact_text(message)

    marker = " with errors: "
    if _skip_log_kind(reason) == "entry" and marker in reason:
        reason = compact_text(reason.split(marker, 1)[1])

    reason = _peel_string_list(reason)
    reason = _RECORD_ID_PATTERN.sub("", reason).strip()

    for prefix in _WRITER_PREFIXES:
        if reason.lower().startswith(prefix.lower()):
            reason = reason[len(prefix) :].strip()

    parts = _VALIDATION_SPLIT.split(reason, maxsplit=1)
    if len(parts) == 2:
        reason = parts[1].strip()

    reason = _CDS_IDS_SUFFIX.sub("", reason).strip()
    reason = _DETAILS_SUFFIX.sub("", reason).strip()
    # Final normalization for stable titles across legacy/new message formats.
    reason = compact_text(reason).lower()
    reason = _VOCAB_TERM_PATTERN.sub(
        r"vocabulary term not found in '\1'.", reason
    )
    reason = _URL_PATTERN.sub("<url>", reason)
    return compact_text(reason) or "Unknown error"


def _normalize_log_hit(hit):
    """Normalize one OpenSearch hit into the report shape.

    Output fields:
      - ``message`` keeps raw indexed text for expanded report lines.
      - ``report_group_key`` is the cleaned grouping title key.
      - ``record_id`` extracts INSPIRE id for links/counts.

    Example output:
      {
        "timestamp": "2026-07-09 10:00",
        "level": "ERROR",
        "message": "[INSPIRE#1] DOI validation failed. | details: doi=bad",
        "record_id": "1",
        "report_group_key": "doi validation failed."
      }
    """
    source = hit.get("_source") or hit
    raw_message = compact_text(source.get("message"))
    level = str(source.get("level", "INFO")).upper()
    if _skip_log_kind(raw_message) == "entry":
        level = "ERROR"
    elif level == "CRITICAL":
        level = "ERROR"

    return {
        "timestamp": format_timestamp(
            source.get("timestamp") or source.get("@timestamp")
        ),
        "level": level,
        "message": raw_message or _("No log message"),
        "record_id": _extract_record_id(raw_message),
        "report_group_key": (
            _unwrap_message(raw_message) if level in _GROUPABLE_LEVELS else None
        ),
    }


def group_log_hits(hits, max_examples=5):
    """Turn OpenSearch hits into grouped report buckets.

    Pipeline per hit:
      1. Normalize hit -> entry dict (raw message + computed group key).
      2. Drop exact duplicates (same timestamp/level/message).
      3. Drop batch skip summaries (``Skipping N transformed entries...``).
      4. Bucket ERROR/WARNING by ``(level, report_group_key)``.
      5. Push INFO/other levels to ``other_lines``.
      6. Build issue cards sorted by count (desc), then time, then title.

    Each issue card contains:
      - ``title``: normalized group key (stable reason, no ``| details:``).
      - ``entries``: raw log lines for expanded drill-down in the UI.
      - ``records`` / ``examples``: INSPIRE ids parsed from raw lines.
      - ``count``: number of unique record ids, or line count if no ids.

    ``error_count`` / ``warning_count`` count **group buckets**, not log lines.

    Example:
        Input hits (2 lines, same root cause, different details):
            "[INSPIRE#1] DOI validation failed. | details: doi=bad-1"
            "[INSPIRE#2] DOI validation failed. | details: doi=bad-2"

        Output grouped_issues (1 bucket):
            title="doi validation failed.", count=2,
            records=["1", "2"],
            entries=[{message: full raw line 1}, {message: full raw line 2}]

        Returns:
            (grouped_issues, other_lines, error_count=1, warning_count=0)
    """
    seen = set()
    buckets = OrderedDict()
    other_lines = []

    for hit in hits:
        entry = _normalize_log_hit(hit)
        skip_kind = _skip_log_kind(entry["message"])

        # Exact-line dedupe: OpenSearch pagination can return duplicates.
        dedupe_key = (entry["timestamp"], entry["level"], entry["message"])
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        # Batch counters from datastream have no per-record context; omit them.
        if skip_kind == "summary":
            continue

        if entry["level"] in _GROUPABLE_LEVELS and entry["report_group_key"]:
            # Bucket identity: same level + same normalized reason => one card.
            bucket = buckets.setdefault(
                (entry["level"], entry["report_group_key"]),
                {
                    "level": entry["level"],
                    "title": entry["report_group_key"],
                    "entries": [],
                    "records": [],
                    "first_timestamp": entry["timestamp"],
                },
            )
            # Keep raw line for expanded view; collect INSPIRE id for links/count.
            bucket["entries"].append(entry)
            if entry["record_id"] and entry["record_id"] not in bucket["records"]:
                bucket["records"].append(entry["record_id"])
        else:
            # INFO and non-groupable lines (success messages, debug noise, etc.).
            other_lines.append(entry)

    grouped_issues = [
        {
            "level": bucket["level"],
            "title": bucket["title"],
            # Prefer unique record count; fall back to line count when no ids.
            "count": len(bucket["records"]) or len(bucket["entries"]),
            "records": bucket["records"],
            "examples": bucket["records"][:max_examples],
            "entries": bucket["entries"],
            "first_timestamp": bucket["first_timestamp"],
        }
        for bucket in buckets.values()
    ]
    # Most frequent failure reasons first.
    grouped_issues.sort(
        key=lambda issue: (-issue["count"], issue["first_timestamp"], issue["title"])
    )

    # Count of grouped buckets (cards), not individual log lines.
    error_count = sum(1 for issue in grouped_issues if issue["level"] == "ERROR")
    warning_count = sum(1 for issue in grouped_issues if issue["level"] == "WARNING")
    return grouped_issues, other_lines, error_count, warning_count


def plain_text_log(run, grouped_issues, other_lines, total, error_count, warning_count):
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

    rendered_lines = sum(len(issue["entries"]) for issue in grouped_issues) + len(
        other_lines
    )
    if total and total > rendered_lines:
        header.append(
            f"Showing first {rendered_lines} of {total} log entries "
            f"(truncated at JOBS_LOGS_MAX_RESULTS={max_results})."
        )
    header.append("=" * 80)

    body = []
    for level in ("ERROR", "WARNING"):
        for issue in grouped_issues:
            if issue["level"] != level:
                continue
            body.append(f"{issue['level']}: {issue['title']}")
            body.extend(
                f"[{entry['timestamp']}] {entry['level']} {entry['message']}"
                for entry in issue["entries"]
            )
            body.append("")
    if other_lines:
        body.append("Other log lines")
        body.extend(
            f"[{entry['timestamp']}] {entry['level']} {entry['message']}"
            for entry in other_lines
        )

    logs = "\n".join(header + body).rstrip()
    if not body:
        logs += "\n" + (run.message or "No logs available for this run.\n")
    return logs


def report_context(run_id):
    """Build context for the colored HTML report page."""
    run = resolve_harvester_run(run_id)
    hits, total = fetch_harvester_run_logs(run)
    grouped_issues, other_lines, error_count, warning_count = group_log_hits(hits)
    status = getattr(run.status, "name", str(run.status))

    rendered_lines = sum(len(issue["entries"]) for issue in grouped_issues) + len(
        other_lines
    )
    truncation_message = None
    if total and total > rendered_lines:
        truncation_message = (
            f"Log results truncated. Too many log results returned ({total}). "
            f"Only the most recent {rendered_lines} results are shown."
        )

    display_title = (getattr(run, "title", None) or "").strip() or f"Run {run.id}"
    return {
        "run": run,
        "title": display_title,
        "status": status,
        "started_at": format_timestamp(run.started_at),
        "finished_at": format_timestamp(run.finished_at) if run.finished_at else None,
        "truncation_message": truncation_message,
        "grouped_errors": [
            issue for issue in grouped_issues if issue["level"] == "ERROR"
        ],
        "grouped_warnings": [
            issue for issue in grouped_issues if issue["level"] == "WARNING"
        ],
        "other_lines": other_lines,
        "error_count": error_count,
        "warning_count": warning_count,
        "inspire_literature_url": INSPIRE_LITERATURE_URL,
    }
