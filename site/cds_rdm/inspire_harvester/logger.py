# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""INSPIRE harvester logging helpers."""

from flask import current_app
from invenio_rdm_records.services.errors import ValidationErrorWithMessageAsList
from invenio_records_resources.errors import (
    _iter_errors_dict,
    validation_error_to_list_errors,
)
from invenio_vocabularies.datastreams.errors import WriterError
from marshmallow import ValidationError

from cds_rdm.utils import compact_text


def _validation_errors_to_text(error_dicts):
    """Turn invenio error dicts into ``field: msg`` strings."""
    parts = []
    for err in error_dicts:
        field = err.get("field", "")
        messages = err.get("messages", [])
        message = ", ".join(compact_text(m) for m in messages if compact_text(m))
        if not message:
            continue
        # Stable title for grouping; keep values after "| details:" for drill-down.
        if message.lower().startswith("duplicated affiliations:"):
            _, _, values = message.partition(":")
            values = compact_text(values)
            message = "Duplicated affiliations."
            if values:
                message = f"{message} | details: {values}"
        parts.append(f"{field}: {message}" if field else message)
    return parts


def _flatten_validation_messages(messages):
    """Flatten validation payloads using invenio-records-resources helpers."""
    if isinstance(messages, dict):
        return _validation_errors_to_text(_iter_errors_dict(messages))

    if isinstance(messages, list):
        parts = []
        for item in messages:
            if isinstance(item, dict) and "messages" in item:
                parts.extend(_validation_errors_to_text([item]))
            elif isinstance(item, dict):
                parts.extend(_validation_errors_to_text(_iter_errors_dict(item)))
            else:
                text = compact_text(item)
                if text:
                    parts.append(text)
        return parts

    text = compact_text(messages)
    return [text] if text else []


def format_validation_error(error):
    """Return a readable validation error summary."""
    if isinstance(error, ValidationError):
        parts = _validation_errors_to_text(validation_error_to_list_errors(error))
    elif isinstance(error, ValidationErrorWithMessageAsList):
        parts = _flatten_validation_messages(error.messages)
    else:
        parts = _flatten_validation_messages(getattr(error, "messages", error))

    return "; ".join(parts) if parts else compact_text(error)


def describe_exception(error):
    """Return a compact exception label for logs and report messages."""
    details = compact_text(error)
    if details:
        return f"{error.__class__.__name__}: {details}"
    return error.__class__.__name__


def raise_unexpected_operation_error(
    *,
    subject,
    action,
    error,
    logger=None,
    inspire_id=None,
    record_pid=None,
    draft_id=None,
    file_key=None,
):
    """Log traceback-rich context and raise a readable writer error."""
    labels = []
    if inspire_id:
        labels.append(f"INSPIRE#{inspire_id}")
    if record_pid:
        labels.append(f"record {record_pid}")
    if draft_id:
        labels.append(f"draft {draft_id}")
    if file_key:
        labels.append(f"file '{file_key}'")

    # Logger keeps record/draft labels for debugging; WriterError text stays
    # id-free so report grouping can key on the failure shape alone.
    log_message = f"Unexpected error while handling {subject}"
    if labels:
        log_message = f"{log_message} ({', '.join(labels)})"

    active_logger = logger or current_app.logger
    active_logger.exception(log_message)

    raise WriterError(
        f"The {subject} could not be {action}. "
        f"| details: {describe_exception(error)}"
    ) from error


class Logger:
    """Logger wrapper class."""

    def __init__(self, inspire_id, record_pid=None):
        """Constructor."""
        self.inspire_id = inspire_id
        self.record_pid = record_pid

    def _prefix(self):
        """Returns the prefix to be used in the log messages."""
        parts = []
        if self.inspire_id:
            parts.append(f"INSPIRE#{self.inspire_id}")
        if self.record_pid:
            parts.append(f"CDS#{self.record_pid}")
        return "[" + " ".join(parts) + "] " if parts else ""

    def info(self, message):
        """Logs an info message."""
        current_app.logger.info(self._prefix() + message)

    def debug(self, message):
        """Logs a debug message."""
        current_app.logger.debug(self._prefix() + message)

    def warning(self, message):
        """Logs a warning message."""
        current_app.logger.warning(self._prefix() + message)

    def error(self, message):
        """Logs an error message."""
        current_app.logger.error(self._prefix() + message)


def hlog(func):
    """Simple decorator that logs before and after calling the method."""

    def wrapper(self, stream_entry, *args, record_pid=None, **kwargs):

        inspire_id = stream_entry.entry["id"]
        logger = Logger(inspire_id=inspire_id, record_pid=record_pid)
        current_app.logger.debug("Call: {}".format(func.__name__))

        result = func(
            self,
            stream_entry,
            *args,
            inspire_id=inspire_id,
            record_pid=record_pid,
            logger=logger,
            **kwargs,
        )

        current_app.logger.debug("Return: {}".format(func.__name__))
        return result

    return wrapper
