# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""INSPIRE to CDS harvester module."""

from collections import Counter

import requests
from flask import current_app
from invenio_access.permissions import system_identity
from invenio_records_resources.proxies import current_service_registry
from invenio_vocabularies.datastreams.errors import WriterError
from opensearchpy import RequestError
from sqlalchemy.exc import NoResultFound


def fetch_prod_parent_and_version(cdsrdm_id):
    """Ask production what parent and version ids belong to this CDSRDM value.

    INSPIRE's CDSRDM can be either the parent id or a version id. They look
    the same (xxxxx-xxxxx), so we cannot tell from the string alone. Production's
    record API always returns both: parent.id and id (the version).
    """
    base = current_app.config["CDS_HARVESTER_PROD_API_URL"].rstrip("/")
    url = f"{base}/api/records/{cdsrdm_id}"
    try:
        response = requests.get(
            url, headers={"Accept": "application/json"}, timeout=60
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise WriterError(
            "Could not fetch the production CDS record needed to remint "
            "parent and version ids on sandbox. "
            f"| details: cdsrdm_id={cdsrdm_id}, error={exc}"
        ) from exc
    data = response.json()
    parent_id = data.get("parent", {}).get("id")
    version_id = data.get("id")
    if not parent_id or not version_id:
        raise WriterError(
            "Production CDS returned a record without parent.id or id, "
            "so sandbox cannot remint the same parent and version ids. "
            f"| details: cdsrdm_id={cdsrdm_id}, "
            f"parent_id={parent_id}, version_id={version_id}"
        )
    return parent_id, version_id


def retrieve_identifiers(identifiers, scheme):
    """Yield identifier values for the given scheme."""
    for ident in identifiers or []:
        if ident.get("scheme") == scheme and ident.get("identifier"):
            yield ident["identifier"]


def _keys_without_empty_values(value):
    """Keys whose values are not None, [] or {} (empty dump placeholders)."""
    return {k for k, v in value.items() if v not in (None, [], {})}


def compare_metadata(a, b):
    """Compare metadata based on id key only."""
    # If both are dicts
    if isinstance(a, dict) and isinstance(b, dict):
        # If both have an id → compare only the id
        if "id" in a and "id" in b:
            return a["id"] == b["id"]

        keys_a, keys_b = _keys_without_empty_values(a), _keys_without_empty_values(b)

        # Otherwise compare keys recursively
        if keys_a != keys_b:
            return False

        return all(compare_metadata(a[k], b[k]) for k in keys_a)

    # If both are lists
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return False
        return all(compare_metadata(x, y) for x, y in zip(a, b))

    # Fallback normal comparison
    return a == b


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
            f"Failed vocabulary search in '{vocab_type}'. "
            f"| details: term={term}, error={e}"
        )
    except NoResultFound as e:
        logger.error(
            f"Vocabulary term not found in '{vocab_type}'. "
            f"| details: term={term}"
        )
        raise e


def _search_vocabulary_id(service, term, vocab_type):
    """Search vocabulary by exact ID match, returning the ID or None."""
    search_term = f'"{term}"' if "/" in term else term
    result = service.search(system_identity, type=vocab_type, q=f'id:"{search_term}"')
    if result.total == 1:
        return list(result.hits)[0]["id"]
    return None


def get_vocabulary_exact(term, vocab_type, ctx, logger):
    """Get vocabulary ID by exact match, with fallback to normalized term."""
    if not term:
        return None

    service = current_service_registry.get("vocabularies")

    try:
        vocab_id = _search_vocabulary_id(service, term, vocab_type)
        if vocab_id:
            return vocab_id

        # Fallback: normalize (uppercase + strip hyphens) and search again
        normalized = term.upper().replace("-", "")
        if normalized != term:
            vocab_id = _search_vocabulary_id(service, normalized, vocab_type)
            if vocab_id:
                return vocab_id

        result = service.search(
            system_identity, type=vocab_type, q=f'props.aliases.keyword:{term}'
        )
        if result.total == 1:
            return list(result.hits)[0]["id"]

        logger.warning(
            f"Vocabulary term not found in '{vocab_type}'. | details: term={term}"
        )
        return None

    except Exception as e:
        logger.error(
            f"Failed vocabulary search in '{vocab_type}'. "
            f"| details: term={term}, error={e}"
        )
        return None
