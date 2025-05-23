# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.


"""CDS-RDM custom fields."""

from invenio_rdm_records.contrib.imprint import IMPRINT_CUSTOM_FIELDS, IMPRINT_NAMESPACE
from invenio_rdm_records.contrib.journal import JOURNAL_CUSTOM_FIELDS, JOURNAL_NAMESPACE
from invenio_rdm_records.contrib.thesis import THESIS_CUSTOM_FIELDS, THESIS_NAMESPACE

from cds_rdm.custom_fields.cern import CERN_CUSTOM_FIELDS, CERN_CUSTOM_FIELDS_UI
from cds_rdm.custom_fields.meeting import (
    MEETING_CUSTOM_FIELDS,
    MEETING_CUSTOM_FIELDS_UI,
    MEETING_NAMESPACE,
)
from cds_rdm.custom_fields.publishing import PUBLISHING_FIELDS_UI

NAMESPACES = {
    "cern": "https://greybook.cern.ch/",
    **JOURNAL_NAMESPACE,
    **IMPRINT_NAMESPACE,
    **THESIS_NAMESPACE,
    **MEETING_NAMESPACE,
}


CUSTOM_FIELDS = [
    *CERN_CUSTOM_FIELDS,
    # journal
    *JOURNAL_CUSTOM_FIELDS,
    # imprint
    *IMPRINT_CUSTOM_FIELDS,
    # thesis
    *THESIS_CUSTOM_FIELDS,
    # meeting
    *MEETING_CUSTOM_FIELDS,
]


# Custom fields UI components
CUSTOM_FIELDS_UI = [
    CERN_CUSTOM_FIELDS_UI,
    # publishing information
    PUBLISHING_FIELDS_UI,
    MEETING_CUSTOM_FIELDS_UI,
]
