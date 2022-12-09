# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""CDS-RDM migration streams module."""
from cds_rdm.migration.transform.user_transform import CDSUserTransform
from invenio_rdm_migrator.streams import StreamDefinition
from cds_rdm.migration.extract import LegacyExtract, LegacyUserExtract
from invenio_rdm_migrator.streams.records.load import RDMRecordCopyLoad
from cds_rdm.migration.transform.transform import CDSToRDMRecordTransform
from invenio_rdm_migrator.streams.users import UserCopyLoad


RecordStreamDefinition = StreamDefinition(
    name="records",
    extract_cls=LegacyExtract,
    transform_cls=CDSToRDMRecordTransform,
    load_cls=RDMRecordCopyLoad,
)
"""ETL stream for CDS to RDM records."""

UserStreamDefinition = StreamDefinition(
    name="users",
    extract_cls=LegacyUserExtract,
    transform_cls=CDSUserTransform,
    load_cls=UserCopyLoad,
)
"""ETL stream for CDS to import users."""
