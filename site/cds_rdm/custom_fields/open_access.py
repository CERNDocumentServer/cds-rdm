# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""CDS-RDM Open Access custom fields."""

from invenio_i18n import lazy_gettext as _
from invenio_vocabularies.services.custom_fields import VocabularyCF

OPEN_ACCESS_CUSTOM_FIELDS = [
    VocabularyCF(
        name="cern:oa_level",
        vocabulary_id="open_access_levels",
        dump_options=True,
        multiple=False,
    ),
    VocabularyCF(
        name="cern:oa_funding_model",
        vocabulary_id="open_access_funding_models",
        dump_options=True,
        multiple=False,
    ),
]

OPEN_ACCESS_CUSTOM_FIELDS_UI = {
    "section": _("Open Access"),
    "active": False,
    "ui_widget": "OpenAccessFields",
    "fields": [
        dict(
            field="cern:oa_level",
            ui_widget="Dropdown",
            props=dict(
                label=_("Open Access Level"),
                icon="lock open",
                description=_("Select the open access level of this record."),
                search=True,
                multiple=False,
                clearable=True,
                autocompleteFrom="/api/vocabularies/open_access_levels",
            ),
        ),
        dict(
            field="cern:oa_funding_model",
            ui_widget="Dropdown",
            props=dict(
                label=_("Funding Model"),
                icon="dollar sign",
                description=_("Select how open access was obtained for this record."),
                search=True,
                multiple=False,
                clearable=True,
                autocompleteFrom="/api/vocabularies/open_access_funding_models",
            ),
        ),
    ],
}
