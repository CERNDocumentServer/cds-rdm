# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the GPL-2.0 License; see LICENSE file for more details.

"""CDS overrides the BibText serializer."""

from flask_resources import BaseListSchema, MarshmallowSerializer
from flask_resources.serializers import SimpleSerializer
from invenio_rdm_records.resources.serializers import BibtexSerializer
from invenio_rdm_records.resources.serializers.bibtex.schema import BibTexSchema


class CDSBibTexSchema(BibTexSchema):
    """CDS-specific BibTex schema."""

    def get_venue(self, obj):
        """Override of the `get_venue` method to support the list-based meeting custom field."""
        meeting = obj.get("custom_fields", {}).get("meeting:meeting", {})
        if isinstance(meeting, list):
            if len(meeting) == 0:
                return None
            meeting = meeting[0]
        return meeting.get("place")


class CDSBibTexSerializer(BibtexSerializer):
    """CDS-specific BibTex serializer for records."""

    def __init__(self, **options):
        """Call MarshmallowSerializer directly (instead of super) to allow overriding object_schema_cls."""
        MarshmallowSerializer.__init__(
            self,
            format_serializer_cls=SimpleSerializer,
            object_schema_cls=CDSBibTexSchema,
            list_schema_cls=BaseListSchema,
            encoder=self.bibtex_tostring,
            **options,
        )
