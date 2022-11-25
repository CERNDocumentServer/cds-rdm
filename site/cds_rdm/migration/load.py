# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""CDS-RDM migration load module."""

from pathlib import Path

from invenio_rdm_migrator.streams.records import RDMRecordCopyLoad


class CDSRecordCopyLoad(RDMRecordCopyLoad):
    def __init__(self, communities_cache, db_uri, tmp_dir):
        tmp_dir = Path(tmp_dir).absolute()
        super().__init__(communities_cache, db_uri, tmp_dir)
