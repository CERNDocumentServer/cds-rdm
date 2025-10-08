# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Errors."""


class CLCSyncError(Exception):
    """Sync entry error exception."""

    def __init__(self, description):
        """Constructor."""
        self.description = description


class CLCSyncNotExistsError(Exception):
    """Sync entry not found exception."""

    def __init__(self, clc_sync_id):
        """Constructor."""
        self.clc_sync_id = clc_sync_id

    @property
    def description(self):
        """Exception's description."""
        return f"Sync entry with id {self.clc_sync_id} is not found."


class CLCSyncAlreadyExistsError(CLCSyncError):
    """Sync entry already exists exception."""
