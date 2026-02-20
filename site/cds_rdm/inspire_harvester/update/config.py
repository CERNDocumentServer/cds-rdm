# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Default field update strategy configuration for the INSPIRE harvester."""

from cds_rdm.inspire_harvester.update.fields.base import (
    ListOfDictAppendUniqueUpdate,
    OverwriteFieldUpdate,
    PreferCurrentMergeDictUpdate,
)
from cds_rdm.inspire_harvester.update.fields.creatibutors import CreatibutorsFieldUpdate
from cds_rdm.inspire_harvester.update.fields.custom_fields import ThesisFieldUpdate
from cds_rdm.inspire_harvester.update.fields.identifiers import (
    IdentifiersFieldUpdate,
    RelatedIdentifiersUpdate,
)
from cds_rdm.inspire_harvester.update.fields.metadata import PublicationDateUpdate

UPDATE_STRATEGY_CONFIG = {
    # fields not included in the strategy raise error on update attempt
    "pids": PreferCurrentMergeDictUpdate(keep_incoming_keys=[]),
    # "files": FilesUpdate(),
    "metadata.resource_type": OverwriteFieldUpdate(),
    "metadata.creators": CreatibutorsFieldUpdate(strict=True),
    "metadata.contributors": CreatibutorsFieldUpdate(strict=False),
    "metadata.identifiers": IdentifiersFieldUpdate(),
    "metadata.related_identifiers": RelatedIdentifiersUpdate(),
    "metadata.publication_date": PublicationDateUpdate(),
    "metadata.subjects":  ListOfDictAppendUniqueUpdate(key_field="subject"),
    "metadata.languages": ListOfDictAppendUniqueUpdate(key_field="id"),
    "metadata.description": OverwriteFieldUpdate(),
    "metadata.title": OverwriteFieldUpdate(),
    "custom_fields.thesis:thesis": ThesisFieldUpdate(),
    "custom_fields.cern:accelerators": ListOfDictAppendUniqueUpdate(key_field="id"),
    "custom_fields.cern:experiments": ListOfDictAppendUniqueUpdate(key_field="id"),
    # "custom_fields.cern:beams": IgnoreFieldUpdate(),
}