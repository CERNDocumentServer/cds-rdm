# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Transformer module."""
from flask import current_app
from invenio_vocabularies.datastreams.transformers import BaseTransformer

from .transform.transform_entry import RDMEntry


class InspireJsonTransformer(BaseTransformer):
    """INSPIRE JSON transformer."""

    def __init__(self, root_element=None, *args, **kwargs):
        """Initializes the transformer."""
        self.root_element = root_element
        super().__init__(*args, **kwargs)

    def apply(self, stream_entry, **kwargs):
        """Applies the transformation to the INSPIRE record entry."""
        current_app.logger.info("Start transformation of INSPIRE record to CDS record.")
        # assign original source record to the stream entry
        stream_entry.source_entry = stream_entry.entry
        entry_builder = RDMEntry(stream_entry.entry)
        rdm_entry, versions, cds_id, errors = entry_builder.build()

        if errors:
            all_errors = "\n".join(errors)
            error_message = (
                f"[INSPIRE#{stream_entry.entry['metadata']['control_number']}] failed transformation. "
                f"Errors:\n{all_errors}"
            )
            stream_entry.errors.append(error_message)

        rdm_entry["_inspire_ctx"] = {"cds_id": cds_id, "versions": versions}
        stream_entry.entry = rdm_entry
        return stream_entry
