# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2025 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""CDS-RDM CERN custom fields."""

from invenio_i18n import lazy_gettext as _
from invenio_records_resources.services.custom_fields import KeywordCF
from invenio_vocabularies.services.custom_fields import VocabularyCF

CERN_CUSTOM_FIELDS = [
    VocabularyCF(
        name="cern:experiments",
        vocabulary_id="experiments",
        dump_options=True,
        multiple=True,
    ),
    VocabularyCF(
        name="cern:departments",
        vocabulary_id="departments",
        dump_options=True,
        multiple=True,
    ),
    VocabularyCF(
        name="cern:accelerators",
        vocabulary_id="accelerators",
        dump_options=True,
        multiple=True,
    ),
    KeywordCF(name="cern:projects", multiple=True),
    KeywordCF(name="cern:facilities", multiple=True),
    KeywordCF(name="cern:studies", multiple=True),
    VocabularyCF(
        name="cern:beams",
        vocabulary_id="beams",
        dump_options=True,
        multiple=True,
    ),
]

CERN_CUSTOM_FIELDS_UI = [
    {
        "section": "Organization",
        "displaySection": False,
        "fields": [
            dict(
                field="cern:departments",
                ui_widget="Dropdown",
                display_url="https://scientific-info.cern/archives/history_CERN/internal_organisation/20s",
                props=dict(
                    label="Department",
                    icon="building",
                    description="Please select a recognised department from the list if applicable e.g BE, EN, HR etc.",
                    search=False,
                    multiple=True,
                    sort_by="title_sort",
                    clearable=True,
                    autocompleteFrom="/api/vocabularies/departments",
                ),
            )
        ],
    },
    {
        "section": "Accelerators and Beams",
        "discoverable_fields": True,  # marks the section with discoverable fields
        "fields": [
            dict(
                field="cern:accelerators",
                ui_widget="Dropdown",
                display_url="https://scientific-info.cern/archives/history_CERN/internal_organisation/20s",
                props=dict(
                    label="Accelerator",
                    icon="bullseye",
                    description="Please select a recognised accelerator from the list if applicable e.g LHC, SPS, PS, R&D etc.",
                    search=False,
                    multiple=True,
                    sort_by="title_sort",
                    clearable=True,
                    type="text",
                    multiple_values=True,
                    autocompleteFrom="/api/vocabularies/accelerators",
                    note=_(
                        "The specific accelerator of the data record, e.g LHC, SPS, PS, R&D etc."
                    ),
                ),
            ),
            dict(
                field="cern:beams",
                ui_widget="Dropdown",
                props=dict(
                    label="Beam",
                    icon="bullseye",
                    description="Please select a recognised beam from the list if applicable e.g H4, X7, T9 etc.",
                    search=False,
                    multiple=True,
                    sort_by="title_sort",
                    clearable=True,
                    type="text",
                    multiple_values=True,
                    autocompleteFrom="/api/vocabularies/beams",
                    note=_("The specific beam of the data record, e.g., H4."),
                ),
            ),
        ],
    },
    {
        "section": "Research activities",
        "discoverable_fields": True,  # marks the section with discoverable fields
        "fields": [
            dict(
                field="cern:experiments",
                ui_widget="AutocompleteDropdown",
                display_url="https://greybook.cern.ch/experiment/list",
                props=dict(
                    label="Experiment",
                    icon="lab",
                    placeholder="Select an experiment",
                    description="You should fill this field with one of the experiments e.g ATLAS, CMS, LHCb etc.",
                    search=True,
                    multiple=True,
                    clearable=True,
                    autocompleteFrom="/api/vocabularies/experiments",
                    note=_(
                        "The specific experiment of the data record, e.g. ATLAS, CMS, LHCb etc."
                    ),
                    type="text",
                    multiple_values=True,
                ),
            ),
            dict(
                field="cern:projects",
                ui_widget="MultiInput",
                props=dict(
                    label=_("Projects"),
                    type="text",
                    description="You should fill this field with one of the projects e.g HL-LHC, HIE-ISOLDE etc.",
                    multiple_values=True,
                    note=_(
                        "The specific project of the data record, e.g HL-LHC, HIE-ISOLDE etc."
                    ),
                ),
            ),
            dict(
                field="cern:studies",
                ui_widget="MultiInput",
                props=dict(
                    label=_("Studies"),
                    type="text",
                    description="You should fill this field with one of the studies e.g CLICdp, VHE-LHC etc.",
                    multiple_values=True,
                    note=_(
                        "The specific study of the data record, e.g CLICdp, VHE-LHC etc."
                    ),
                ),
            ),
            dict(
                field="cern:facilities",
                ui_widget="MultiInput",
                props=dict(
                    label=_("Facilities"),
                    type="text",
                    description="You should fill this field with one of the research facilities e.g ISOLDE, HiRadMat etc.",
                    multiple_values=True,
                    note=_(
                        "The specific facility beam of the data record, e.g ISOLDE, HiRadMat etc."
                    ),
                ),
            ),
        ],
    },
]
