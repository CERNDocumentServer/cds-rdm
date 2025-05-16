# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Configuration."""

from invenio_i18n import lazy_gettext as _
from invenio_records_resources.services.records.facets import TermsFacet

# Not working yet
CLC_SYNC_FACETS = {
    "status": {
        "facet": TermsFacet(
            field="status",
            title=_("Status"),
        ),
        "ui": {
            "field": "status",
        },
    },
}
"""Facets/aggregations for CLC user sync results."""

CLC_SYNC_DEFAULT_QUEUE = None
"""Default Celery queue."""

CLC_SYNC_SORT_OPTIONS = {
    "created": dict(
        title=_("Created"),
        fields=["created"],
    ),
    "status": dict(
        title=_("Status"),
        fields=["status"],
    ),
}
"""Definitions of available CLC user sync sort options. """

CLC_SYNC_SEARCH = {
    "facets": ["status"],
    "sort": ["created", "status"],
}
"""CLC user sync search configuration."""

CLC_SYNC_ALLOWED_RESOURCE_TYPES = [
    "publication",
]
"""Allowed resource types for CLC user sync."""

CLC_URL_SYNC = "CHANGE_ME"
"""URL for the CLC endpoint."""

CDS_ILS_IMPORTER_API_KEY = "CHANGE_ME"
"""API key for the CLC importer. This is a placeholder and should be replaced with a real key."""
