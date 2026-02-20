# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""INSPIRE to CDS harvester module."""

from collections import Counter

from invenio_access.permissions import system_identity
from invenio_records_resources.proxies import current_service_registry
from opensearchpy import RequestError
from sqlalchemy.exc import NoResultFound


def assert_unique_ids(mappers):
    """Assert that all mapper IDs are unique."""
    ids = [m.id for m in mappers]
    counts = Counter(ids)
    dupes = [mid for mid, c in counts.items() if c > 1]
    if dupes:
        raise ValueError(f"Duplicate mapper ids in pipeline: {dupes}")


def get_path(record, path):
    """Get value of dict from dotted path."""
    cur = record
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur

def set_path(doc, path, value) -> None:
    """Set value of dict at the given path."""
    parts = path.split(".")
    cur = doc
    for p in parts[:-1]:
        cur = cur.setdefault(p, {})
    cur[parts[-1]] = value


def build_path(path, value):
    """Build nested dict from dotted path."""
    keys = path.split(".")
    d = {}
    cur = d
    for k in keys[:-1]:
        cur[k] = {}
        cur = cur[k]
    cur[keys[-1]] = value
    return d


def deep_merge(a, b):
    """Merge b into a (non-destructive) and return new dict."""
    out = dict(a)
    for k, v in b.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def deep_merge_all(parts):
    """Deep merge all parts into a single dictionary."""
    out = {}
    for p in parts:
        if p is not None:
            out = deep_merge(out, p)
    return out


def search_vocabulary(term, vocab_type, ctx, logger):
    """Search vocabulary utility function."""
    service = current_service_registry.get("vocabularies")
    if "/" in term:
        # escape the slashes
        term = f'"{term}"'
    try:
        vocabulary_result = service.search(
            system_identity, type=vocab_type, q=f'id:"{term}"'
        )
        return vocabulary_result
    except RequestError as e:
        logger.error(
            f"Failed vocabulary search ['{term}'] in '{vocab_type}'. INSPIRE#: {ctx.inspire_id}. Error: {e}."
        )
    except NoResultFound as e:
        logger.error(
            f"Vocabulary term ['{term}'] not found in '{vocab_type}'. INSPIRE#: {ctx.inspire_id}"
        )
        raise e
