# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.


"""CDS-RDM custom fields."""
from functools import partial, wraps

from invenio_i18n import lazy_gettext as _

# attention! keep the imports below even if unused
from invenio_rdm_records.contrib.meeting import MEETING_NAMESPACE
from invenio_rdm_records.contrib.meeting.custom_fields import MeetingCF
from invenio_rdm_records.contrib.meeting.processors import (
    MeetingCSLDumper,
    MeetingDublinCoreDumper,
)
from invenio_rdm_records.services.schemas.metadata import (
    _valid_url,
    record_related_identifiers_schemes,
)
from marshmallow import fields
from marshmallow_utils.fields import IdentifierValueSet, SanitizedUnicode
from marshmallow_utils.schemas import IdentifierSchema


def _support_meeting_list(post_dump):
    """Upstream dumpers expect a dict; CDS stores meeting as a list."""

    @wraps(post_dump)
    def wrapper(self, data, original=None, **kwargs):
        original = dict(original or {})
        custom_fields = dict(original.get("custom_fields") or {})
        meeting = custom_fields.get("meeting:meeting")
        if isinstance(meeting, list):
            custom_fields["meeting:meeting"] = meeting[0] if meeting else {}
            original["custom_fields"] = custom_fields
        return post_dump(self, data, original=original, **kwargs)

    return wrapper


MeetingCSLDumper.post_dump = _support_meeting_list(MeetingCSLDumper.post_dump)
MeetingDublinCoreDumper.post_dump = _support_meeting_list(
    MeetingDublinCoreDumper.post_dump
)


class CDSMeetingCF(MeetingCF):
    """Nested custom field."""

    @property
    def field(self):
        """Meeting fields definitions."""
        return fields.List(fields.Nested(
            {
                "acronym": SanitizedUnicode(),
                "dates": SanitizedUnicode(),
                "place": SanitizedUnicode(),
                "session_part": SanitizedUnicode(),
                "session": SanitizedUnicode(),
                "title": SanitizedUnicode(),
                # URL left for backwards compat, unused
                "url": SanitizedUnicode(
                    validate=_valid_url(error_msg=_("You must provide a valid URL.")),
                ),
                "identifiers": IdentifierValueSet(
                    fields.Nested(
                        partial(
                            IdentifierSchema,
                            allowed_schemes=record_related_identifiers_schemes,
                        )
                    )
                ),
            }
        ))

    @property
    def mapping(self):
        """Meeting search mappings."""
        return {
            "type": "object",
            "properties": {
                "acronym": {"type": "keyword"},
                "dates": {"type": "keyword"},
                "place": {"type": "text"},
                "session_part": {"type": "keyword"},
                "session": {"type": "keyword"},
                "title": {
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword"}},
                },
                # URL left for backwards compat, unused
                "url": {"type": "keyword"},
                "identifiers": {
                    "type": "object",
                    "properties": {
                        "identifier": {"type": "keyword"},
                        "scheme": {"type": "keyword"},
                    },
                },
            },
        }


MEETING_CUSTOM_FIELDS = [
    CDSMeetingCF(name="meeting:meeting"),
]


MEETING_CUSTOM_FIELDS_UI = {
    "section": _("Conference"),
    "active": False,
    "fields": [
        {
            "field": "meeting:meeting",
            "ui_widget": "CDSMeeting",
            "template": "CDSMeeting.html",
            "props": {
                "title": {
                    "label": _("Title"),
                    "placeholder": "",
                    "description": "",
                },
                "acronym": {
                    "label": _("Acronym"),
                    "placeholder": "",
                    "description": "",
                },
                "dates": {
                    "label": _("Dates"),
                    "placeholder": _("e.g. 21-22 November 2022."),
                    "description": "",
                },
                "place": {
                    "label": _("Place"),
                    "placeholder": "",
                    "description": _("Location where the conference took place."),
                },
                "identifiers": {
                    "label": _("Identifiers"),
                    "description": _("URL of conference website or other identifier."),
                },
                "session": {
                    "label": _("Session"),
                    "placeholder": _("e.g. VI"),
                    "description": _("Session within the conference."),
                },
                "session_part": {
                    "label": _("Part"),
                    "placeholder": _("e.g. 1"),
                    "description": _("Part within the session."),
                },
            },
        }
    ],
}
