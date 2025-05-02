from invenio_i18n import lazy_gettext as _
# keep the imports below
from invenio_rdm_records.contrib.meeting import (
    MEETING_CUSTOM_FIELDS,
    MEETING_NAMESPACE,
)

MEETING_CUSTOM_FIELDS_UI = {
    "section": _("Conference"),
    "fields": [
        {
            "field": "meeting:meeting",
            "ui_widget": "CDSMeeting",
            "template": "meeting.html",
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
