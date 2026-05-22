# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""CDS-RDM publishing fields."""

from invenio_i18n import lazy_gettext as _
from invenio_rdm_records.contrib.imprint import IMPRINT_CUSTOM_FIELDS_UI
from invenio_rdm_records.contrib.journal import JOURNAL_CUSTOM_FIELDS_UI
from invenio_rdm_records.contrib.thesis import THESIS_CUSTOM_FIELDS_UI
from invenio_vocabularies.services.custom_fields import VocabularyCF

PUBLISHING_CUSTOM_FIELDS = [
    VocabularyCF(
        name="cern:oa_funding_model",
        vocabulary_id="open_access_funding_models",
        dump_options=True,
        multiple=False,
    ),
]

PUBLISHING_FIELDS_UI = {
    "section": _("Publishing information (Imprint, Journal, Thesis)"),
    "hide_from_landing_page": True,
    # hide meeting section from Additional details in landing page
    "ui_widget": "CERNPublication",
    "active": True,  # collapsed by default
    "fields": [
        # journal
        *JOURNAL_CUSTOM_FIELDS_UI["fields"]
        + [
            dict(
                field="cern:oa_funding_model",
                ui_widget="Dropdown",
                props=dict(
                    label=_("Publication funding model"),
                    icon="dollar sign",
                    description=_(
                        "Optionally select how open access was obtained for this publication. Check https://sis.web.cern.ch/practical-information/faq/open-access-publishing for more info"
                    ),
                    search=True,
                    multiple=False,
                    clearable=True,
                    autocompleteFrom="/api/vocabularies/open_access_funding_models",
                ),
            ),
        ],
        # imprint
        *IMPRINT_CUSTOM_FIELDS_UI["fields"],
        # thesis
        *THESIS_CUSTOM_FIELDS_UI["fields"],
    ],
}
