#
# This file is part of Invenio.
# Copyright (C) 2016-2018 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Creation of CDS RDM migration models."""

import sqlalchemy as sa
from alembic import op
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

    op.create_table(
        "cds_migration_legacy_affiliations_mapping",
        sa.Column("id", UUIDType(), nullable=False),
        sa.Column("legacy_affiliation_input", sa.String, nullable=False),
        sa.Column("ror_exact_match", sa.String, nullable=True),
        sa.Column("ror_not_exact_match", sa.String, nullable=True),
        sa.Column(
            "ror_match_info",
            JSONType().with_variant(
                sa.dialects.postgresql.JSON(none_as_null=True),
                "postgresql",
            ),
            nullable=True,
        ),
        sa.Column(
            "curated_affiliation",
            JSONType().with_variant(
                sa.dialects.postgresql.JSON(none_as_null=True),
                "postgresql",
            ),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "idx_legacy_affiliation_input",
        "cds_migration_legacy_affiliations_mapping",
        ["legacy_affiliation_input"],
        unique=True,
    )


def downgrade():
    """Downgrade database."""
    op.drop_table("cds_migration_legacy_records")
    op.drop_table("cds_migration_legacy_affiliations_mapping")
