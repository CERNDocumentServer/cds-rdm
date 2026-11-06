# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Committee approval community model."""

import uuid
from datetime import date

from invenio_communities.communities.records.models import CommunityMetadata
from invenio_db import db
from invenio_db.shared import Timestamp
from sqlalchemy import func, or_
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy_utils.types import UUIDType


class CommitteeApprovalEnrollment(db.Model, Timestamp):
    """A community enrolled in the publication approval workflow."""

    __tablename__ = "cds_committee_approval_enrollment"

    id = db.Column(UUIDType, primary_key=True, default=uuid.uuid4)

    community_id = db.Column(
        UUIDType,
        db.ForeignKey("communities_metadata.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        comment="The enrolled community",
    )

    label = db.Column(
        db.String(255),
        nullable=False,
        comment="Workflow label shown in the UI, e.g. 'EP approval'",
    )
    committee_name = db.Column(
        db.String(255),
        nullable=True,
        comment="Reviewer/board name shown in review-step labels, e.g. 'EP Board'",
    )
    referee_group = db.Column(
        db.String(80),
        db.ForeignKey("accounts_role.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Id of the group (role) whose members act as referees",
    )
    read_only = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        comment="Only allow read-only access to the workflow in this community",
    )

    report_number_prefix = db.Column(
        db.String(255),
        nullable=False,
        comment="Fixed prefix, e.g. 'CERN-EP'",
    )
    report_number_include_year = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        comment="Append the current year after the prefix",
    )
    report_number_counter_digits = db.Column(
        db.Integer,
        nullable=False,
        default=3,
        comment="Zero-padding width of the counter",
    )

    community = db.relationship("CommunityMetadata", lazy="joined")
    referee_role = db.relationship("Role", lazy="joined")

    def report_number_scan_prefix(self, year=None):
        """Return the prefix shared by this community's report numbers.

        E.g. ``CERN-EP-2026-`` (or ``CERN-EP-`` if the year is not included).
        """
        if not self.report_number_include_year:
            return f"{self.report_number_prefix}-"
        year = year or date.today().year
        return f"{self.report_number_prefix}-{year}-"

    def format_report_number(self, sequence, year=None):
        """Return the report number for the given counter value."""
        digits = self.report_number_counter_digits
        return f"{self.report_number_scan_prefix(year)}{sequence:0{digits}d}"

    @classmethod
    def get_by_id(cls, id):
        """Get entry by its id."""
        return db.session.get(cls, id)

    @classmethod
    def get_by_community_id(cls, community_id):
        """Get entry by community id."""
        return cls.query.filter_by(community_id=community_id).one_or_none()

    @classmethod
    def get_report_number_prefixes(cls):
        """Return the set of report number prefixes of all enrolled communities."""
        return {
            prefix
            for (prefix,) in db.session.query(cls.report_number_prefix).distinct()
        }

    @classmethod
    def get_all(cls):
        """Return all entries."""
        return cls.query.all()

    @classmethod
    def create(cls, data):
        """Create an entry."""
        with db.session.begin_nested():
            obj = cls(**data)
            db.session.add(obj)
        return obj

    @classmethod
    def update(cls, obj, data):
        """Update an entry."""
        with db.session.begin_nested():
            for key, value in data.items():
                setattr(obj, key, value)
        return obj

    @classmethod
    def delete(cls, obj):
        """Delete an entry."""
        with db.session.begin_nested():
            db.session.delete(obj)

    @classmethod
    def _filtered_query(cls, params, skip_facet=None):
        """Build the query for the free-text search and the active facet filters.

        ``skip_facet`` leaves out one facet's own filter, so that its counts
        still show the other available values.
        """
        query = cls.query
        if q := params.get("q"):
            community_title = func.jsonb_extract_path_text(
                db.cast(CommunityMetadata.json, JSONB), "metadata", "title"
            )
            query = query.join(cls.community).filter(
                or_(
                    CommunityMetadata.slug.ilike(f"%{q}%"),
                    community_title.ilike(f"%{q}%"),
                    cls.referee_group.ilike(f"%{q}%"),
                    cls.report_number_prefix.ilike(f"%{q}%"),
                )
            )
        facets = params.get("facets") or {}
        if facets.get("read_only") and skip_facet != "read_only":
            values = [v.lower() == "true" for v in facets["read_only"]]
            query = query.filter(cls.read_only.in_(values))
        return query

    @classmethod
    def _aggregations(cls, params):
        """Compute the facet buckets."""
        read_only_rows = (
            cls._filtered_query(params, skip_facet="read_only")
            .with_entities(cls.read_only, func.count(cls.id))
            .group_by(cls.read_only)
            .all()
        )
        return {
            "read_only": {
                "buckets": [
                    {
                        "key": "true" if value else "false",
                        "doc_count": count,
                        "label": "Yes" if value else "No",
                    }
                    for value, count in read_only_rows
                ],
            },
        }

    @classmethod
    def search(cls, params):
        """Search entries."""
        query = cls._filtered_query(params)
        sort = params.get("sort")
        if sort in ("label", "created", "referee_group", "report_number_prefix"):
            query = query.order_by(getattr(cls, sort))
        else:
            query = query.order_by(cls.created)
        size = int(params.get("size", 25))
        page = int(params.get("page", 1))
        total = query.count()
        hits = query.offset((page - 1) * size).limit(size).all()
        return {
            "hits": hits,
            "total": total,
            "aggregations": cls._aggregations(params),
        }
