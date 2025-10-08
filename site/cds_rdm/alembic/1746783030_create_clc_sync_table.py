#
# This file is part of Invenio.
# Copyright (C) 2016-2018 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Create CLC sync table."""

import sqlalchemy as sa
import sqlalchemy_utils
from alembic import op
from sqlalchemy.dialects import mysql, postgresql

from cds_rdm.clc_sync.models import SyncStatusEnum

# revision identifiers, used by Alembic.
revision = "1746783030"
down_revision = "35c1075e6360"
branch_labels = ()
depends_on = None


def upgrade():
    """Upgrade database."""
    op.create_table(
        "cds_clc_record_sync",
        sa.Column("id", sqlalchemy_utils.types.uuid.UUIDType(), nullable=False),
        sa.Column(
            "parent_record_pid",
            sa.String(),
            nullable=True,
            comment="The record id in CDS",
        ),
        sa.Column(
            "clc_record_pid", sa.String(), nullable=True, comment="The record id in CLC"
        ),
        sa.Column(
            "status",
            sqlalchemy_utils.types.choice.ChoiceType(SyncStatusEnum, impl=sa.String(1)),
            nullable=False,
            comment="Synchronisation status",
        ),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column(
            "auto_sync",
            sa.Boolean(),
            nullable=False,
            comment="Indicates if auto-sync should occur on record edit",
        ),
        sa.Column(
            "last_sync",
            sa.DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql"),
            nullable=True,
            comment="Last sync time",
        ),
        sa.Column(
            "created",
            sa.DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql"),
            nullable=False,
        ),
        sa.Column(
            "updated",
            sa.DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cds_clc_record_sync")),
        sa.UniqueConstraint(
            "parent_record_pid",
            "clc_record_pid",
            name="uq_cds_clc_record_sync_parent_record_pid",
        ),
    )
    op.create_index(
        "idx_cls_record_pid", "cds_clc_record_sync", ["clc_record_pid"], unique=True
    )
    op.create_index(
        "idx_parent_record_pid",
        "cds_clc_record_sync",
        ["parent_record_pid"],
        unique=True,
    )


def downgrade():
    """Downgrade database."""
    op.drop_index("idx_parent_record_pid", table_name="cds_clc_record_sync")
    op.drop_index("idx_cls_record_pid", table_name="cds_clc_record_sync")
    op.drop_table("cds_clc_record_sync")
