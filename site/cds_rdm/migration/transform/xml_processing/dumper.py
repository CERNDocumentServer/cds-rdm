# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""CDS-RDM MARC XML dumper module."""

import arrow

from cds_dojson.marc21.utils import create_record

from cds_rdm.migration.transform import migrator_marc21


class CDSRecordDump:
    """CDS record dump class."""

    def __init__(
        self,
        data,
        source_type="marcxml",
        latest_only=True,
        dojson_model=migrator_marc21,
    ):

        """Initialize."""
        self.data = data
        self.source_type = source_type
        self.latest_only = latest_only
        self.dojson_model = dojson_model
        self.revisions = None
        self.files = None

    @property
    def created(self):
        """Get creation date."""
        return self.revisions[0][0]

    def prepare_revisions(self):
        """Prepare revisions."""
        # TODO get all revisions
        latest = self.data["record"][-1]
        self.revisions = [self._prepare_revision(latest)]

    def prepare_files(self):
        """Get files from data dump."""
        # Prepare files
        files = {}
        for f in self.data["files"]:
            k = f["full_name"]
            if k not in files:
                files[k] = []
            files[k].append(f)

        # Sort versions
        for k in files.keys():
            files[k].sort(key=lambda x: x["version"])

        self.files = files

    def _prepare_revision(self, data):
        timestamp = arrow.get(data["modification_datetime"]).datetime

        # exception_handlers = {
        #     UnexpectedValue: migration_exception_handler,
        #     MissingRequiredField: migration_exception_handler,
        #     ManualImportRequired: migration_exception_handler,
        # }

        marc_record = create_record(data["marcxml"])
        try:
            json_converted_record = self.dojson_model.do(
                marc_record,
                # exception_handlers=exception_handlers
            )
        except Exception as e:
            raise e
            # raise JSONConversionException(e)
        missing = self.dojson_model.missing(marc_record)
        # if missing:
        #     raise LossyConversion(missing=missing)
        return timestamp, json_converted_record
