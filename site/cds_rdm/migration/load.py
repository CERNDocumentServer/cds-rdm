# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""CDS-RDM migration load module."""

from pathlib import Path

from invenio_rdm_migrator.streams.records import RDMRecordCopyLoad

from invenio_rdm_migrator.load.base import Load
from invenio_rdm_records.proxies import current_rdm_records_service
from invenio_access.permissions import system_identity

class CDSRecordCopyLoad(RDMRecordCopyLoad):
    """CDSRecordCopyLoad."""

    def __init__(self, communities_cache, db_uri, tmp_dir):
        """Constructor."""
        tmp_dir = Path(tmp_dir).absolute()
        super().__init__(communities_cache, db_uri, tmp_dir)


class CDSRecordServiceLoad(Load):
    """CDSRecordServiceLoad."""
    
    def __init__(self, db_uri, data_dir, tmp_dir, existing_data=False, entries=None):
        """Constructor."""
        self.db_uri = db_uri
        self.data_dir = data_dir
        self.tmp_dir = tmp_dir
        self.existing_data = existing_data
        self.entries = entries
        
    def _prepare(self, entry):
        """Prepare the record"""
        pass

    def _load(self, entry):
        """Use the services to load the entries."""
        identity = system_identity # Should we create an idenity for the migration?
        draft = current_rdm_records_service.create(identity, entry["record"]["json"])
        current_rdm_records_service.publish(system_identity, draft["id"])
    
    def _cleanup(self, *args, **kwargs):
        """Cleanup the entries."""
        pass
    
    