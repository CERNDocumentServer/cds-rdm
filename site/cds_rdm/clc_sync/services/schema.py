# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""CDS-RDM CLC schema sync module."""

from flask import current_app
from marshmallow import EXCLUDE, Schema, fields

from cds_rdm.clc_sync.models import SyncStatusEnum


class CLCSyncSchema(Schema):
    """Schema for CLCSync."""

    class Meta:
        """Meta attributes for schema."""

        unknown = EXCLUDE

    parent_record_pid = fields.String(required=True)
    clc_record_pid = fields.String(allow_none=True)
    status = fields.Method(serialize="get_status", deserialize="load_status")
    message = fields.String(allow_none=True)
    auto_sync = fields.Boolean()
    created = fields.String(dump_only=True)
    id = fields.String(dump_only=True)
    clc_url = fields.Method(serialize="get_clc_url", dump_only=True)
    last_sync = fields.DateTime(format="iso", allow_none=True)

    def get_clc_url(self, obj):
        """Generate the CLC URL for the record."""
        base_url = current_app.config["CLC_URL_SYNC"]
        return (
            f"{base_url}literature/{obj.clc_record_pid}" if obj.clc_record_pid else None
        )

    def get_status(self, obj):
        """Get the status of the record."""
        return obj.status.name if isinstance(obj.status, SyncStatusEnum) else obj.status

    def load_status(self, value):
        """Load the status of the record."""
        try:
            return SyncStatusEnum[value]
        except KeyError:
            return value
