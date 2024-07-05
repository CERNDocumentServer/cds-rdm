# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""CDS-RDM migration streams module."""
from invenio_rdm_migrator.streams import StreamDefinition
from invenio_rdm_migrator.streams.records.load import RDMRecordCopyLoad
from invenio_rdm_migrator.streams.users import UserCopyLoad

from cds_rdm.migration.extract import LegacyExtract, LegacyUserExtract
from cds_rdm.migration.transform.transform import CDSToRDMRecordTransform
from cds_rdm.migration.transform.user_transform import CDSUserTransform
from .load import CDSRecordServiceLoad

RecordStreamDefinition = StreamDefinition(
    name="records",
    extract_cls=LegacyExtract,
    transform_cls=CDSToRDMRecordTransform,
    load_cls=CDSRecordServiceLoad,
)
"""ETL stream for CDS to RDM records."""
