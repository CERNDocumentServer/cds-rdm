# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2024 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Minters."""

from invenio_pidstore.models import PersistentIdentifier, PIDStatus


def legacy_recid_minter(legacy_recid, uuid):
    """Legacy_recid minter."""
    PersistentIdentifier.create(
        pid_type="lrecid",
        pid_value=legacy_recid,
        object_type="rec",
        object_uuid=uuid,
        status=PIDStatus.REGISTERED,
    )
