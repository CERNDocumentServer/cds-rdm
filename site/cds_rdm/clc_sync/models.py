# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.
"""CDS Migration models."""
import enum
import uuid
from datetime import datetime

from invenio_db import db
from invenio_records.models import Timestamp
from sqlalchemy import Column, String, UniqueConstraint, or_
from sqlalchemy.dialects import mysql
from sqlalchemy_utils import ChoiceType
from sqlalchemy_utils.types import UUIDType

from cds_rdm.clc_sync.services.errors import CLCSyncNotExistsError


class SyncStatusEnum(enum.Enum):
    """Enumeration of a run's possible states."""

    SUCCESS = "S"
    FAILED = "F"
    PENDING = "P"


class CDSToCLCSyncModel(db.Model, Timestamp):
    """Store the sync information between CDS and CLC."""

    __tablename__ = "cds_clc_record_sync"
    __table_args__ = (
        db.Index("idx_parent_record_pid", "parent_record_pid", unique=True),
        db.Index("idx_cls_record_pid", "clc_record_pid", unique=True),
        UniqueConstraint(
            "parent_record_pid",
            "clc_record_pid",
            name="uq_cds_clc_record_sync_parent_record_pid",
        ),
    )

    id = db.Column(
        UUIDType,
        primary_key=True,
        default=uuid.uuid4,
    )

    parent_record_pid = Column(
        String,
        comment="The record id in CDS",
    )
    clc_record_pid = Column(String, nullable=True, comment="The record id in CLC")

    status = db.Column(
        ChoiceType(SyncStatusEnum, impl=db.String(1)),
        nullable=False,
        comment="Synchronisation status",
    )

    message = db.Column(db.Text, nullable=True)

    auto_sync = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        comment="Indicates if auto-sync should occur on record edit",
    )

    last_sync = db.Column(
        db.DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql"),
        default=datetime.utcnow,
        nullable=True,
        comment="Last sync time",
    )

    @classmethod
    def create(cls, data):
        """Create a new sync entry."""
        with db.session.begin_nested():
            obj = cls(
                message=data.get("message"),
                status=data.get("status"),
                clc_record_pid=data.get("clc_record_pid"),
                parent_record_pid=data.get("parent_record_pid"),
            )
            db.session.add(obj)

        return obj

    @classmethod
    def update(cls, data, id):
        """Update an existing sync entry and return the updated object."""
        with db.session.begin_nested():
            sync_entry = db.session.get(cls, id)
            if not sync_entry:
                raise CLCSyncNotExistsError(id)

            for key, value in data.items():
                setattr(sync_entry, key, value)

        return sync_entry

    @classmethod
    def get_by_id(cls, id):
        """Get sync entry by internal UUID."""
        sync_entry = db.session.get(cls, id)
        if sync_entry:
            return sync_entry
        raise CLCSyncNotExistsError(id)

    @classmethod
    def get_by_parent_record_pid(cls, parent_record_pid):
        """Get record by its parent_record_pid."""
        sync_entry = (
            db.session.query(cls)
            .filter_by(parent_record_pid=parent_record_pid)
            .one_or_none()
        )
        if sync_entry:
            return sync_entry

        raise CLCSyncNotExistsError(parent_record_pid)

    @classmethod
    def delete(cls, sync_entry):
        """Delete sync entry."""
        with db.session.begin_nested():
            db.session.delete(sync_entry)

    @classmethod
    def search(cls, params):
        """Search for sync entries with flexible word matching."""
        query = db.session.query(cls)

        if params.get("status"):
            query = query.filter_by(status=params["status"])

        if params.get("clc_record_pid"):
            query = query.filter_by(clc_record_pid=params["clc_record_pid"])

        if params.get("parent_record_pid"):
            query = query.filter_by(parent_record_pid=params["parent_record_pid"])

        if q := params.get("q"):
            query = query.filter(
                or_(
                    cls.clc_record_pid.ilike(f"%{q}%"),
                    cls.parent_record_pid.ilike(f"%{q}%"),
                )
            )
        size = params.get("size", 25)
        page = params.get("page", 1)
        offset = (page - 1) * size

        total = query.count()
        hits = query.offset(offset).limit(size).all()

        return {"hits": hits, "total": total}
