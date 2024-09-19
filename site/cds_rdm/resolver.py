# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2024 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Resolver."""

from invenio_pidstore.models import PersistentIdentifier


def get_pid_by_legacy_recid(legacy_recid):
    """Get record by pid value."""
    recid = PersistentIdentifier.query.filter_by(
        pid_value=legacy_recid, pid_type="lrecid"
    ).one()
    obj_uuid = recid.object_uuid
    pid = PersistentIdentifier.query.filter_by(
        object_uuid=obj_uuid, pid_type="recid"
    ).one()
    return pid.pid_value
