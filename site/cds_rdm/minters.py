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
    alt_id_scheme_names = current_app.config["CDS_CERN_ALTERNATE_IDENTIFIERS_TO_MINT"]
    alternate_identifiers = {
        id["scheme"]: id["identifier"]
        for id in draft["metadata"].get("identifiers", [])
        if id["scheme"] in alt_id_scheme_names.keys()
    }

    # Query all existing PIDs for the CURRENT record and these schemes
    existing_pids = {
        pid.pid_type: pid
        for pid in PersistentIdentifier.query.filter(
            PersistentIdentifier.object_type == "rec",
            PersistentIdentifier.object_uuid == uuid,
            PersistentIdentifier.pid_type.in_(alt_id_scheme_names.keys()),
        )
    }

    # Delete PIDs in DB that are not present in the data anymore
    for scheme, pid in existing_pids.items():
        if scheme not in alternate_identifiers:
            db.session.delete(pid)
            db.session.commit()

    # Update existing PIDs if the value has changed, or add new ones if they are not present
    for scheme, value in alternate_identifiers.items():
        pid = existing_pids.get(scheme, None)
        if pid:
            if pid.pid_value != value:
                pid.pid_value = value
                pid.status = PIDStatus.REGISTERED
                db.session.commit()
        else:
            PersistentIdentifier.create(
                pid_type=scheme,
                pid_value=value,
                object_type="rec",
                object_uuid=uuid,
                status=PIDStatus.REGISTERED,
            )
