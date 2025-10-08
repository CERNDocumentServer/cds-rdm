# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Transformer module."""
from flask import current_app
from invenio_vocabularies.datastreams.transformers import BaseTransformer

from .transform_entry import RDMEntry


class InspireJsonTransformer(BaseTransformer):
    """INSPIRE JSON transformer."""

    def __init__(self, root_element=None, *args, **kwargs):
        """Initializes the transformer."""
        self.root_element = root_element
        super().__init__(*args, **kwargs)

    def apply(self, stream_entry, **kwargs):
        """Applies the transformation to the INSPIRE record entry."""
        current_app.logger.info("Start transformation of INSPIRE record to CDS record.")
        rdm_entry, errors = RDMEntry(stream_entry.entry).build()

        if errors:
            all_errors = "\n".join(errors)
            error_message = (
                f"INSPIRE record #{stream_entry.entry['metadata']['control_number']} failed transformation. "
                f"See errors:\n{all_errors}"
            )
            stream_entry.errors.append(error_message)

        stream_entry.entry = rdm_entry
        return stream_entry
