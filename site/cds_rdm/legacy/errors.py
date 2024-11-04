# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""CDS-RDM legacy redirection exceptions."""


class VersionNotFound(Exception):
    """Error for when the specific version of a record is not found."""

    def __init__(self, version, latest_record):
        """Initialise error."""
        self.version = version
        self.latest_record = latest_record
