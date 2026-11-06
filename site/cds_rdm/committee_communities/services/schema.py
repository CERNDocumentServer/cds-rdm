# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Committee approval communities schema."""

from invenio_accounts.models import Role
from invenio_communities.communities.records.models import CommunityMetadata
from invenio_db import db
from marshmallow import EXCLUDE, Schema, ValidationError, fields, validate, validates


class CommitteeApprovalCommunitySchema(Schema):
    """Schema for a committee approval community entry."""

    class Meta:
        """Meta attributes."""

        unknown = EXCLUDE

    id = fields.String(dump_only=True)
    community_id = fields.String(required=True)
    community_slug = fields.Method("get_community_slug", dump_only=True)
    community_title = fields.Method("get_community_title", dump_only=True)
    label = fields.String(required=True, validate=validate.Length(min=1, max=255))
    committee_name = fields.String(
        allow_none=True, validate=validate.Length(max=255), load_default=None
    )
    referee_group = fields.String(
        required=True, validate=validate.Length(min=1, max=80)
    )
    referee_group_name = fields.Method("get_referee_group_name", dump_only=True)
    read_only = fields.Boolean(load_default=False)
    report_number_prefix = fields.String(
        required=True, validate=validate.Length(min=1, max=255)
    )
    report_number_include_year = fields.Boolean(load_default=True)
    report_number_counter_digits = fields.Integer(
        load_default=3, validate=validate.Range(min=1, max=10)
    )
    created = fields.DateTime(dump_only=True)
    updated = fields.DateTime(dump_only=True)

    def get_community_slug(self, obj):
        """Return the slug of the enrolled community."""
        return obj.community.slug if obj.community else None

    def get_referee_group_name(self, obj):
        """Return the name of the referee group."""
        return obj.referee_role.name if obj.referee_role else None

    def get_community_title(self, obj):
        """Return the title of the enrolled community."""
        if not obj.community:
            return None
        return (obj.community.json or {}).get("metadata", {}).get("title")

    @validates("referee_group")
    def validate_referee_group(self, value, **kwargs):
        """Check that the group exists."""
        if db.session.get(Role, value) is None:
            raise ValidationError("Group does not exist.")

    @validates("community_id")
    def validate_community_id(self, value, **kwargs):
        """Check that the community exists."""
        try:
            exists = db.session.get(CommunityMetadata, value) is not None
        except Exception:
            exists = False
        if not exists:
            raise ValidationError("Community does not exist.")
