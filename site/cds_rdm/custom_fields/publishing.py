# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2025 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""CDS-RDM publishing fields."""

from invenio_i18n import lazy_gettext as _
from invenio_rdm_records.contrib.imprint import IMPRINT_CUSTOM_FIELDS_UI
from invenio_rdm_records.contrib.journal import JOURNAL_CUSTOM_FIELDS_UI
from invenio_rdm_records.contrib.thesis import THESIS_CUSTOM_FIELDS_UI

PUBLISHING_FIELDS_UI = {
    "section": _("Publishing information (Imprint, Journal, Thesis)"),
    "hide_from_landing_page": False,  # hide meeting section from Additional details in landing page
    "active": False,  # collapsed by deafault
    "fields": [
        # journal
        *JOURNAL_CUSTOM_FIELDS_UI["fields"],
        # imprint
        *IMPRINT_CUSTOM_FIELDS_UI["fields"],
        # thesis
        *THESIS_CUSTOM_FIELDS_UI["fields"],
    ],
}
