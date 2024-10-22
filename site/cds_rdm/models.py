# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2024 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

"""CDS Migration models."""

import json
import uuid

from invenio_db import db
from sqlalchemy import Column, Integer
from sqlalchemy.dialects import postgresql
from sqlalchemy_utils.types import UUIDType


class CDSMigrationLegacyRecord(db.Model):
    """Store the extracted legacy information for a specific record."""

    __tablename__ = "cds_migration_legacy_records"

    id = db.Column(
        UUIDType,
        primary_key=True,
        default=uuid.uuid4,
    )
    parent_object_uuid = Column(
        UUIDType,
        nullable=True,
        comment="The uuid of the record metadata of the created parent record after migration.",
    )
    migrated_record_object_uuid = Column(
        UUIDType,
        nullable=True,
        comment="The uuid of the record metadata of the latest record metadata at the time of the migration. This is important as every version of the new system (metadata wise) was created based on that legacy record revision.",
    )
    legacy_recid = Column(
        Integer, nullable=True, comment="The record id in the legacy system"
    )
    json = db.Column(
        db.JSON().with_variant(
            postgresql.JSONB(none_as_null=True),
            "postgresql",
        ),
        default=lambda: dict(),
        nullable=True,
        comment="The extracted information of the legacy record before any transformation.",
    )

    def __repr__(self):
        """Representation of the model."""
        return f"<CDSMigrationLegacyRecord legacy_recid={self.legacy_recid} parent_object_uuid={self.parent_object_uuid} migrated_record_object_uuid={self.migrated_record_object_uuid} json={json.dumps(self.json)}>"
