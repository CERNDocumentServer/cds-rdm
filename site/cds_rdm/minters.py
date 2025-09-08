# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2024 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Minters."""

from flask import current_app
from invenio_db import db
from invenio_pidstore.models import PersistentIdentifier, PIDStatus
from sqlalchemy import and_, or_


def legacy_recid_minter(legacy_recid, uuid):
    """Legacy_recid minter."""
    PersistentIdentifier.create(
        pid_type="lrecid",
        pid_value=legacy_recid,
        object_type="rec",
        object_uuid=uuid,
        status=PIDStatus.REGISTERED,
    )


def alternate_identifier_minter(uuid, draft):
    """Alternative identifier minter."""
    alt_id_scheme_names = current_app.config["CDS_CERN_MINT_ALTERNATE_IDS"].keys()

    # Can be multiple values with same scheme
    # Can be same value with different schemes
    alt_ids_in_draft = []
    for id in draft["metadata"].get("identifiers", []):
        scheme = id.get("scheme")
        value = id.get("identifier")
        if scheme in alt_id_scheme_names:
            alt_ids_in_draft.append((scheme, value))

    # Query all existing PIDs for the CURRENT record and these schemes, for faster lookup
    existing_pids_in_db = PersistentIdentifier.query.filter(
        PersistentIdentifier.object_type == "rec",
        PersistentIdentifier.object_uuid == uuid,
        PersistentIdentifier.pid_type.in_(alt_id_scheme_names),
    ).all()
    existing_pids = {}
    for pid in existing_pids_in_db:
        existing_pids[(pid.pid_type, pid.pid_value)] = pid

    # Delete PIDs in DB that are not present in the data anymore
    for (pid_type, pid_value), pid in existing_pids.items():
        if (pid_type, pid_value) not in alt_ids_in_draft:
            db.session.delete(pid)
            db.session.commit()

    # For each value in the incoming data, look up the existing PIDs, if not present, create a new PID
    for scheme, value in alt_ids_in_draft:
        if (scheme, value) not in existing_pids:
            PersistentIdentifier.create(
                pid_type=scheme,
                pid_value=value,
                object_type="rec",
                object_uuid=uuid,
                status=PIDStatus.REGISTERED,
            )
