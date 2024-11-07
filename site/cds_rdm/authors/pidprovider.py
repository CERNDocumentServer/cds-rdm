# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2024 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.


"""CDS RDM PID providers."""

from __future__ import absolute_import

from base32_lib import base32
from invenio_pidstore.providers.recordid_v2 import RecordIdProviderV2


class AuthorIdProvider(RecordIdProviderV2):
    """Author identifier provider."""

    pid_type = "autid"
    """Type of persistent identifier."""

    @classmethod
    def generate_id(cls, options=None):
        """Generate author id."""
        _id = base32.generate(length=10, split_every=0, checksum=True)
        return "cds:a:" + _id
