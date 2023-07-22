# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""CDS-RDM exceptions."""

from invenio_i18n import lazy_gettext as _


class GroupSyncingError(Exception):
    """Group base syncing exception."""


class RequestError(GroupSyncingError):
    """The provided set spec does not exist."""

    def __init__(self, url, error_details):
        """Initialise error."""
        super().__init__(_(f"Request error on {url}.\n Error details: {error_details}"))
