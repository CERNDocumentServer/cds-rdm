# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""CDS-RDM migration streams module."""

from invenio_rdm_migrator.streams import Stream, StreamDefinition
from cds_rdm.migration.extract import LegacyExtract
from invenio_rdm_migrator.streams.records.load import RDMRecordCopyLoad
from cds_rdm.migration.transform.transform import CDSToRDMRecordTransform


class RecordStream(Stream):
    """ETL stream for Zenodo to RDM records."""


RecordStreamDefinition = StreamDefinition(
    name="records",
    extract_cls=LegacyExtract,
    transform_cls=CDSToRDMRecordTransform,
    load_cls=RDMRecordCopyLoad,
)