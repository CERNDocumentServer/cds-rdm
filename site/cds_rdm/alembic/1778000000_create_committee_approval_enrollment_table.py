# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Create committee approval enrollment table."""

import sqlalchemy as sa
import sqlalchemy_utils
from alembic import op

# revision identifiers, used by Alembic.
revision = "1778000000"
down_revision = "1771314900"
branch_labels = ()
depends_on = "de9c14cbb0b2"  # invenio-communities: communities tables


def upgrade():
    """Upgrade database."""
    op.create_table(
        "cds_committee_approval_enrollment",
        sa.Column("id", sqlalchemy_utils.types.uuid.UUIDType(), nullable=False),
        sa.Column(
            "community_id",
            sqlalchemy_utils.types.uuid.UUIDType(),
            nullable=False,
            comment="The enrolled community",
        ),
        sa.Column(
            "label",
            sa.String(length=255),
            nullable=False,
            comment="Workflow label shown in the UI, e.g. 'EP approval'",
        ),
        sa.Column(
            "committee_name",
            sa.String(length=255),
            nullable=True,
            comment="Reviewer/board name shown in review-step labels, e.g. 'EP Board'",
        ),
        sa.Column(
            "referee_group",
            sa.String(length=80),
            nullable=False,
            comment="Id of the group (role) whose members act as referees",
        ),
        sa.Column(
            "read_only",
            sa.Boolean(),
            nullable=False,
            comment="Only allow read-only access to the workflow in this community",
        ),
        sa.Column(
            "report_number_prefix",
            sa.String(length=255),
            nullable=False,
            comment="Fixed prefix, e.g. 'CERN-EP'",
        ),
        sa.Column(
            "report_number_include_year",
            sa.Boolean(),
            nullable=False,
            comment="Append the current year after the prefix",
        ),
        sa.Column(
            "report_number_counter_digits",
            sa.Integer(),
            nullable=False,
            comment="Zero-padding width of the counter",
        ),
        sa.Column(
            "created",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["community_id"],
            ["communities_metadata.id"],
            name=op.f("fk_cds_committee_approval_enrollment_community_id_commu_d461"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["referee_group"],
            ["accounts_role.id"],
            name=op.f("fk_cds_committee_approval_enrollment_referee_group_acco_7c22"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id", name=op.f("pk_cds_committee_approval_enrollment")
        ),
        sa.UniqueConstraint(
            "community_id",
            name=op.f("uq_cds_committee_approval_enrollment_community_id"),
        ),
    )


def downgrade():
    """Downgrade database."""
    op.drop_table("cds_committee_approval_enrollment")
