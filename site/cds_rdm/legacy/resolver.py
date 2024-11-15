# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2024 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Resolver."""

from flask import g
from invenio_pidstore.models import PersistentIdentifier
from invenio_rdm_records.proxies import current_rdm_records_service
from invenio_search.engine import dsl

from .errors import VersionNotFound


def get_pid_by_legacy_recid(legacy_recid):
    """Get record by pid value."""
    # Get the object uuid from pidstore
    recid = PersistentIdentifier.query.filter_by(
        pid_value=legacy_recid, object_type="rec", pid_type="lrecid"
    ).one()

    # Use the object uuid to get the parent pid value
    parent_pid = PersistentIdentifier.query.filter_by(
        object_uuid=recid.object_uuid, object_type="rec", pid_type="recid"
    ).one()

    return parent_pid


def get_record_by_version(parent_pid_value, version):
    """Get record by parent pid value and version."""
    latest_record = current_rdm_records_service.read_latest(
        identity=g.identity, id_=parent_pid_value
    )
    if not version or version == "all" or latest_record["versions"]["index"] == version:
        return latest_record

    # Use the version number to get the desired record pid value
    hits = current_rdm_records_service.search_versions(
        identity=g.identity,
        id_=latest_record["id"],
        extra_filter=dsl.Q("term", **{"versions.index": version}),
    ).to_dict()["hits"]["hits"]
    if not hits:
        # If record is not found, that means the version doesn't exist
        raise VersionNotFound(version=version, latest_record=latest_record)
    return hits[0]
