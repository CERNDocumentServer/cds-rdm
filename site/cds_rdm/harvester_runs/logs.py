# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Helpers for INSPIRE harvester run logs."""

import ast
import uuid
from collections import OrderedDict
from datetime import datetime

from flask import current_app
from flask_babel import format_datetime
from invenio_i18n import gettext as _
from invenio_jobs.models import Run
from invenio_search import current_search_client
from invenio_search.utils import prefix_index

INSPIRE_HARVESTER_TASK = "process_inspire"
INSPIRE_LITERATURE_URL = "https://inspirehep.net/literature/"
BRACKET_INSPIRE_PREFIX = "[INSPIRE#"
BRACKET_ENTRY_PREFIX = "[entry_id="
SKIPPED_ENTRY_PREFIX = "Skipped entry "
SKIPPED_ENTRY_DELIMITER = " with errors: "
VOCABULARY_WARNING_PREFIX = "Vocabulary term '"
VOCABULARY_WARNING_DELIMITER = "' not found in '"


class HarvesterRunError(Exception):
    """Error raised when a requested harvester run cannot be used."""

    def __init__(self, message, code):
        """Constructor."""
        self.message = message
        self.code = code
        super().__init__(message)


def format_timestamp(value):
    """Format timestamps for display."""
    if value in (None, ""):
        return "N/A"
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return str(value)
    return format_datetime(dt, "yyyy-MM-dd HH:mm")


# String helpers -------------------------------------------------------------

def _compact(value):
    """Collapse whitespace while keeping the original text readable."""
    text = str(value or "").replace("\\n", " ").replace("\n", " ")
    return " ".join(text.split()).strip()


def _remove_prefix(text, prefix):
    """Remove a prefix when present."""
    return text[len(prefix) :] if text.startswith(prefix) else text


def _extract_bracket_value(text, prefix):
    """Extract ``[prefixVALUE]`` blocks from a message."""
    text = str(text or "")
    start = text.find(prefix)
    if start == -1:
        return None
    value_start = start + len(prefix)
    value_end = text.find("]", value_start)
    if value_end == -1:
        return None
    value = text[value_start:value_end].strip()
    return value or None


def _extract_identifier_after(text, marker):
    """Extract an identifier that immediately follows a marker."""
    text = str(text or "")
    start = text.find(marker)
    if start == -1:
        return None
    cursor = start + len(marker)
    while cursor < len(text) and text[cursor].isspace():
        cursor += 1

    end = cursor
    while end < len(text) and (
        text[end].isalnum() or text[end] in {"_", "-"}
    ):
        end += 1

    value = text[cursor:end].strip()
    return value or None


def _extract_entry_id_from_dict(text):
    """Extract ``id`` from a stringified entry dictionary when possible."""
    text = str(text or "").strip()
    if not text.startswith("{"):
        return None
    try:
        parsed = ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return None
    if isinstance(parsed, dict):
        value = parsed.get("id")
        return str(value) if value not in (None, "") else None
    return None


def _strip_leading_bracket_prefixes(message):
    """Drop leading ``[prefix]`` blocks from a log line."""
    text = _compact(message)
    while text.startswith("["):
        end = text.find("]")
        if end == -1:
            break
        text = text[end + 1 :].lstrip()
    return text


def _remove_bracket_block(text, prefix):
    """Remove ``[prefixVALUE]`` blocks wherever they appear."""
    text = str(text or "")
    while True:
        start = text.find(prefix)
        if start == -1:
            return text
        end = text.find("]", start + len(prefix))
        if end == -1:
            return text
        text = f"{text[:start]} {text[end + 1:]}"


def _strip_inline_inspire_ids(text):
    """Remove inline ``INSPIRE#123`` and ``INSPIRE:123`` references."""
    result = []
    for token in str(text or "").split():
        cleaned = token.strip(".,;:()[]")
        if cleaned.startswith(("INSPIRE#", "INSPIRE:")):
            continue
        result.append(token)
    return " ".join(result)


def _is_skip_summary_message(message):
    """Return True for ``Skipping N transformed entries with errors`` lines."""
    text = _compact(message).rstrip(".").lower()
    return text.startswith("skipping ") and text.endswith(
        " transformed entries with errors"
    )


def _parse_vocabulary_warning(reason):
    """Extract term and vocabulary name from a vocabulary warning."""
    reason = _compact(reason)
    if not reason.startswith(VOCABULARY_WARNING_PREFIX):
        return None

    tail = reason[len(VOCABULARY_WARNING_PREFIX) :]
    term, separator, remainder = tail.partition(VOCABULARY_WARNING_DELIMITER)
    if not separator:
        return None

    vocab_type = remainder.rstrip(".")
    if vocab_type.endswith("'"):
        vocab_type = vocab_type[:-1]
    if not term or not vocab_type:
        return None
    return term, vocab_type


def _extract_draft_id(message):
    """Extract the draft id from a draft-related log line."""
    text = _message_without_record_prefix(message)
    if not text.startswith("Draft "):
        return None
    parts = text.split()
    return parts[1].rstrip(".") if len(parts) > 1 else None


def _leading_inspire_prefix(message):
    """Return the leading ``[INSPIRE#...]`` block when present."""
    prefix = _extract_bracket_value(message, BRACKET_INSPIRE_PREFIX)
    return f"{BRACKET_INSPIRE_PREFIX}{prefix}]" if prefix else ""


# Structured log helpers -----------------------------------------------------

def _source(hit):
    """Return the normalized log payload."""
    return hit.get("_source") or hit


def _nested_value(data, *path):
    """Read a nested value from a dictionary."""
    value = data
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
        if value is None:
            return None
    return value


def _first_value(data, *paths):
    """Return the first non-empty value from the provided paths."""
    for path in paths:
        if isinstance(path, str):
            value = data.get(path)
        else:
            value = _nested_value(data, *path)
        if value not in (None, ""):
            return value
    return None


def _run_stats(run):
    """Build a compact summary of record counters for the run."""
    labels = (
        ("inserted_entries_count", _("inserted")),
        ("updated_entries_count", _("updated")),
        ("errored_entries_count", _("errored")),
    )
    parts = []
    for field_name, label in labels:
        value = getattr(run, field_name, None)
        if value:
            parts.append(f"{value} {label}")
    return " · ".join(parts)


# Log parsing helpers --------------------------------------------------------

def _extract_inspire_id(message):
    """Extract INSPIRE id from a log message when present."""
    return (
        _extract_bracket_value(message, BRACKET_INSPIRE_PREFIX)
        or _extract_identifier_after(message, "INSPIRE#")
        or _extract_identifier_after(message, "INSPIRE:")
    )


def _extract_entry_id(message):
    """Extract entry id from a log message when present."""
    return _extract_bracket_value(
        message, BRACKET_ENTRY_PREFIX
    ) or _extract_entry_id_from_dict(message)


def _message_without_record_prefix(message):
    """Strip INSPIRE/CDS prefixes before matching log patterns."""
    return _strip_leading_bracket_prefixes(message).strip()


def _is_skip_summary_log(message):
    """Return True for legacy batch-summary skip messages."""
    return _is_skip_summary_message(message)


def _is_generic_draft_deleted(message):
    """Return True for legacy draft-rollback lines without error details."""
    text = _message_without_record_prefix(message).rstrip(".").lower()
    return (
        text.startswith("draft ")
        and (
            " deleted due to errors" in text
            or " is deleted due to errors" in text
            or " deleted after create failed" in text
        )
    )


def _flatten_error_payload(value, prefix=""):
    """Flatten nested error payloads into readable field messages."""
    if isinstance(value, dict):
        parts = []
        for key, item in value.items():
            key_text = "" if isinstance(key, int) else str(key)
            next_prefix = prefix
            if key_text:
                next_prefix = f"{prefix}.{key_text}" if prefix else key_text
            parts.extend(_flatten_error_payload(item, next_prefix))
        return parts

    if isinstance(value, list):
        if value and all(not isinstance(item, (dict, list)) for item in value):
            message = ", ".join(_compact(item) for item in value if _compact(item))
            if not message:
                return []
            return [f"{prefix}: {message}" if prefix else message]

        parts = []
        for item in value:
            parts.extend(_flatten_error_payload(item, prefix))
        return parts

    text = _compact(value)
    if not text:
        return []
    return [f"{prefix}: {text}" if prefix else text]


# Error payload decoding -----------------------------------------------------

def _decode_error_repr(value):
    """Decode Python-style list/dict error payloads when present."""
    text = str(value or "").strip()
    if not (text.startswith("[") or text.startswith("{")):
        return text
    try:
        parsed = ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return text

    parts = _flatten_error_payload(parsed)
    return "; ".join(parts) if parts else text


def _parse_skipped_entry_message(message):
    """Extract the entry id and inner error from a legacy skipped-entry message."""
    compact_message = _compact(message)
    if not compact_message.startswith(SKIPPED_ENTRY_PREFIX):
        return None, None
    entry_payload, separator, errors_payload = compact_message[
        len(SKIPPED_ENTRY_PREFIX) :
    ].partition(SKIPPED_ENTRY_DELIMITER)
    if not separator:
        return None, None

    entry_id = _extract_entry_id(entry_payload)
    errors = _decode_error_repr(errors_payload)
    return entry_id, errors


def _humanize_reason(reason):
    """Turn internal log text into a readable group title."""
    reason = _decode_error_repr(_compact(reason))
    reason = _remove_bracket_block(reason, BRACKET_ENTRY_PREFIX)
    reason = _remove_bracket_block(reason, BRACKET_INSPIRE_PREFIX)
    reason = _strip_inline_inspire_ids(reason)
    reason = reason.replace("failed transformation. Errors:", "")
    reason = reason.replace("Errors:", "")
    reason = reason.replace("failed transformation.", "")
    reason = _compact(reason)

    if _is_skip_summary_message(reason):
        return "Entries were skipped because they already had errors."
    if reason.startswith("Multiple records match:"):
        return "Multiple CDS records match this INSPIRE record."
    if reason == "Thesis publication date missing (thesis_info and imprint).":
        return (
            "The INSPIRE thesis record is missing a publication date in both "
            "thesis_info and imprint."
        )
    if reason.startswith("checksum: Field may not be null."):
        return "File upload failed because the checksum is missing."

    vocabulary_match = _parse_vocabulary_warning(reason)
    if vocabulary_match:
        term, vocab_type = vocabulary_match
        return (
            f"The vocabulary value '{term}' is missing from the CDS "
            f"'{vocab_type}' vocabulary."
        )

    if " not published because of validation errors: " in reason:
        subject, details = reason.split(
            " not published because of validation errors: ",
            1,
        )
        subject = subject[:1].upper() + subject[1:]
        return (
            f"{subject} could not be published because it failed "
            f"validation: {details}"
        )

    return reason


def _is_skipped_entry_log(message, report_kind):
    """Return True when the log line represents a skipped entry/error."""
    if report_kind == "skipped_entry":
        return True
    compact_message = _compact(message)
    return compact_message.startswith(SKIPPED_ENTRY_PREFIX) or _is_skip_summary_message(
        compact_message
    )


# Grouping helpers -----------------------------------------------------------

def _collect_detailed_errors_by_record(hits):
    """Map record ids to the most useful error line logged for that record."""
    details = {}
    for hit in hits:
        source = _source(hit)
        message = _compact(source.get("message"))
        if _is_generic_draft_deleted(message) or _is_skip_summary_log(message):
            continue
        level = str(source.get("level") or "").upper()
        if level not in {"ERROR", "WARNING"}:
            continue
        record_id = _extract_inspire_id(message) or _extract_entry_id(message)
        if not record_id:
            continue
        detail = _message_without_record_prefix(message)
        if not any(
            marker in detail
            for marker in (
                "Validation error while processing entry",
                "Error while processing entry",
                "deleted after",
                "not published",
                "validation errors",
                "checksum:",
                "Field may not be null",
                "does not have a checksum",
            )
        ):
            continue
        details[str(record_id)] = detail
    return details


def _enrich_draft_deleted_message(message, details_by_record):
    """Attach the underlying failure to legacy draft-deletion log lines."""
    if not _is_generic_draft_deleted(message):
        return message

    record_id = _extract_inspire_id(message) or _extract_entry_id(message)
    draft_id = _extract_draft_id(message) or "unknown"
    detail = details_by_record.get(str(record_id)) if record_id else None
    if not detail:
        return message

    prefix = _leading_inspire_prefix(message)
    if prefix:
        prefix = f"{prefix} "
    return f"{prefix}Draft {draft_id} deleted: {detail}"


def _is_non_actionable_log(message):
    """Return True for side-effect log lines that should not become failure groups."""
    compact_message = _message_without_record_prefix(message)
    return _is_skip_summary_log(compact_message)


def _message_reason(message):
    """Build a grouping key from the visible log message."""
    reason = _compact(message)
    _entry_id, skipped_reason = _parse_skipped_entry_message(reason)
    if skipped_reason:
        return skipped_reason
    reason = _message_without_record_prefix(reason)
    if reason.startswith("Draft ") and " deleted: " in reason:
        reason = reason.split(" deleted: ", 1)[1]
    reason = _remove_prefix(reason, "Error while processing entry:")
    reason = _remove_prefix(reason.lstrip(), "Validation error while processing entry:")
    reason = _remove_prefix(reason.lstrip(), SKIPPED_ENTRY_PREFIX)
    reason = _remove_bracket_block(reason, BRACKET_ENTRY_PREFIX)
    if SKIPPED_ENTRY_DELIMITER in reason:
        reason = reason.split(SKIPPED_ENTRY_DELIMITER, 1)[1]
    return _compact(reason)


def _normalize_log_hit(hit, details_by_record=None):
    """Convert a raw log hit into the fields used by the report view."""
    source = _source(hit)
    message = _compact(source.get("message"))
    if details_by_record:
        message = _enrich_draft_deleted_message(message, details_by_record)
    reason = _compact(
        _first_value(source, "report_reason", ("extra", "report_reason"))
    )
    group_key = _compact(
        _first_value(
            source,
            "report_group_key",
            ("extra", "report_group_key"),
        )
        or reason
    )
    level = str(source.get("level") or "INFO").upper()
    report_kind = _first_value(source, "report_kind", ("extra", "report_kind"))
    effective_level = (
        "ERROR" if _is_skipped_entry_log(message, report_kind) else level
    )
    if effective_level == "CRITICAL":
        effective_level = "ERROR"

    inspire_id = _first_value(
        source,
        "inspire_id",
        ("extra", "inspire_id"),
        ("context", "inspire_id"),
    )
    if inspire_id is None:
        inspire_id = _extract_inspire_id(message)
    entry_id = _first_value(
        source,
        "entry_id",
        ("extra", "entry_id"),
        ("entry", "id"),
    )
    if entry_id is None:
        entry_id = _extract_entry_id(message)
    skipped_entry_id, skipped_reason = _parse_skipped_entry_message(message)
    if entry_id is None and skipped_entry_id is not None:
        entry_id = skipped_entry_id
    if inspire_id is None and entry_id is not None:
        inspire_id = entry_id

    fallback_reason = _message_reason(message)
    raw_reason = reason or fallback_reason
    raw_group_key = group_key or raw_reason
    stable_group_key = _humanize_reason(group_key or fallback_reason)
    if _is_skipped_entry_log(message, report_kind):
        raw_group_key = raw_reason
        stable_group_key = _humanize_reason(raw_reason)

    reason = _humanize_reason(raw_reason)
    group_key = stable_group_key

    raw_message = message or _("No log message")
    return {
        "timestamp": format_timestamp(
            _first_value(source, "timestamp", "@timestamp")
        ),
        "level": effective_level,
        "message": raw_message,
        "display_message": reason or raw_message,
        "report_kind": report_kind,
        "raw_report_reason": raw_reason,
        "raw_report_group_key": raw_group_key,
        "report_reason": reason,
        "report_group_key": group_key,
        "inspire_id": str(inspire_id) if inspire_id is not None else None,
        "entry_id": str(entry_id) if entry_id is not None else None,
        "record_id": (
            str(inspire_id)
            if inspire_id is not None
            else str(entry_id) if entry_id is not None else None
        ),
    }


def _format_plain_text_line(entry):
    """Render a single log line for the download view."""
    return f"[{entry['timestamp']}] {entry['level']} {entry['display_message']}".rstrip()


# Run resolution and fetching ------------------------------------------------

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
    """Return ``(hits, total)`` for a harvester run."""
    try:
        full_index_name = prefix_index(current_app.config["JOBS_LOGGING_INDEX"])
        max_results = current_app.config.get("JOBS_LOGS_MAX_RESULTS", 2000)
        search_query = {
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"context.run_id": str(run.id)}},
                        {"term": {"context.job_id": str(run.job_id)}},
                    ]
                }
            },
            "sort": [
                {"@timestamp": {"order": "asc"}},
                {"_id": {"order": "asc"}},
            ],
            "size": max_results,
            "track_total_hits": True,
        }
        response = current_search_client.search(
            index=full_index_name,
            body=search_query,
        )
        hits = response.get("hits", {}).get("hits", [])
        total = response.get("hits", {}).get("total", {}).get("value", len(hits))
    except Exception:
        current_app.logger.exception(
            "Failed to fetch structured job logs for harvester run %s", run.id
        )
        hits = []
        total = 0
    return hits, total


def group_log_hits(hits, max_examples=5):
    """Group structured warning/error log hits by their report key."""
    details_by_record = _collect_detailed_errors_by_record(hits)
    records_with_draft_deleted = set()
    for hit in hits:
        message = _compact(_source(hit).get("message"))
        if _is_generic_draft_deleted(message):
            record_id = _extract_inspire_id(message) or _extract_entry_id(message)
            if record_id:
                records_with_draft_deleted.add(str(record_id))

    seen = set()
    buckets = OrderedDict()
    other_lines = []

    for hit in hits:
        raw_message = _compact(_source(hit).get("message"))
        entry = _normalize_log_hit(hit, details_by_record)
        if _is_non_actionable_log(entry["message"]):
            continue

        record_id = str(entry.get("record_id") or "")
        if (
            record_id in records_with_draft_deleted
            and not _is_generic_draft_deleted(raw_message)
            and record_id in details_by_record
            and _message_without_record_prefix(raw_message).rstrip(".")
            == details_by_record[record_id].rstrip(".")
        ):
            continue

        dedupe_key = (
            entry["timestamp"],
            entry["level"],
            entry["message"],
            entry["record_id"],
        )
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        if entry["level"] in {"ERROR", "WARNING"} and entry["report_group_key"]:
            bucket_key = (entry["level"], entry["report_group_key"])
            bucket = buckets.setdefault(
                bucket_key,
                {
                    "level": entry["level"],
                    "title": (
                        entry["raw_report_reason"] or entry["raw_report_group_key"]
                    ),
                    "entries": [],
                    "records": [],
                    "examples": [],
                    "first_timestamp": entry["timestamp"],
                },
            )
            bucket["entries"].append(entry)
            if entry["record_id"] and entry["record_id"] not in bucket["records"]:
                bucket["records"].append(entry["record_id"])
            if entry["inspire_id"] and entry["inspire_id"] not in bucket["examples"]:
                bucket["examples"].append(entry["inspire_id"])
            continue

        other_lines.append(entry)

    grouped_issues = []
    for bucket in buckets.values():
        grouped_issues.append(
            {
                "level": bucket["level"],
                "title": bucket["title"],
                "count": len(bucket["records"]) or len(bucket["entries"]),
                "records": bucket["records"],
                "examples": bucket["examples"][:max_examples],
                "entries": bucket["entries"],
                "first_timestamp": bucket["first_timestamp"],
            }
        )

    grouped_issues.sort(
        key=lambda issue: (-issue["count"], issue["first_timestamp"], issue["title"])
    )

    error_count = sum(1 for issue in grouped_issues if issue["level"] == "ERROR")
    warning_count = sum(1 for issue in grouped_issues if issue["level"] == "WARNING")
    return grouped_issues, other_lines, error_count, warning_count


# Report rendering -----------------------------------------------------------

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

    run_stats = _run_stats(run)
    if run_stats:
        header.append(f"Records: {run_stats}")

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
        summary.append(_("%(count)s grouped error(s) found below", count=error_count))
    if warning_count:
        summary.append(
            _("%(count)s grouped warning(s) found below", count=warning_count)
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
    for issue in grouped_issues:
        body.append(f"{issue['level']}: {issue['title']}")
        if issue["records"]:
            body.append("Affected records: " + ", ".join(issue["records"]))
        body.extend(_format_plain_text_line(entry) for entry in issue["entries"])
        body.append("")

    if other_lines:
        body.append("Other log lines")
        body.append("-" * 80)
        body.extend(_format_plain_text_line(entry) for entry in other_lines)

    logs = "\n".join(header + body).rstrip()
    if not body:
        logs += "\n" + (run.message or "No logs available for this run.")
    return logs + "\n"


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
        "run_stats": _run_stats(run),
        "failure_summary_lines": [
            line.strip() for line in (run.message or "").splitlines() if line.strip()
        ],
        "inspire_literature_url": INSPIRE_LITERATURE_URL,
    }
