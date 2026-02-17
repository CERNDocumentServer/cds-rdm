#
# This file is part of Invenio.
# Copyright (C) 2026 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""change datetime types."""

from invenio_db.utils import (
    update_table_columns_column_type_to_datetime,
    update_table_columns_column_type_to_utc_datetime,
)

# revision identifiers, used by Alembic.
revision = "1771314900"
down_revision = "1746783030"
branch_labels = ()
depends_on = None


def upgrade():
    """Upgrade database."""
    update_table_columns_column_type_to_utc_datetime("cds_clc_record_sync", "last_sync")
    update_table_columns_column_type_to_utc_datetime("cds_clc_record_sync", "created")
    update_table_columns_column_type_to_utc_datetime("cds_clc_record_sync", "updated")


def downgrade():
    """Downgrade database."""
    update_table_columns_column_type_to_datetime("cds_clc_record_sync", "last_sync")
    update_table_columns_column_type_to_datetime("cds_clc_record_sync", "created")
    update_table_columns_column_type_to_datetime("cds_clc_record_sync", "updated")
