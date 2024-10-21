#
# This file is part of Invenio.
# Copyright (C) 2016-2018 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Creation of CDS RDM migration models."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy_utils.types import JSONType, UUIDType


# revision identifiers, used by Alembic.
revision = "dd80f65f557b"
down_revision = "a3957490361d"
branch_labels = ()
depends_on = None


def upgrade():
    """Upgrade database."""
    op.create_table(
        "cds_migration_legacy_records",
        sa.Column("id", UUIDType(), nullable=False),
        sa.Column(
            "json",
            JSONType().with_variant(
                sa.dialects.postgresql.JSON(none_as_null=True),
                "postgresql",
            ),
            nullable=True,
        ),
        sa.Column("parent_object_uuid", UUIDType, nullable=True),
        sa.Column("migrated_record_object_uuid", UUIDType, nullable=True),
        sa.Column("legacy_recid", sa.Integer, nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    """Downgrade database."""
    op.drop_table("cds_migration_legacy_records")
