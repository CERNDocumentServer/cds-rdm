# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2025 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""DOI validator for cds."""

from invenio_i18n import lazy_gettext as _
from invenio_rdm_records.services.errors import ValidationErrorWithMessageAsList


def validate_optional_doi_transitions(
    current_draft, previous_published_record, errors=None
):
    """Validates the transitions of DOI for a record when editing or publishing.

    Args:
        current_draft (dict): The current draft being validated.
        previous_published_record (dict or None): The previously published version
            of the record, if it exists. None if the record is being published for
            the first time.
        errors (list, optional): A list to collect validation error messages. If
            provided, errors will be appended to this list. If not provided, a
            ValidationErrorWithMessageAsList will be raised for validation failures.

    Returns:
        dict: A dictionary containing:
            - allowed_providers (list): A list of allowed DOI providers for the
              current record.
            - message (str): An informational message to be shown in the UI for
              the disallowed DOI providers.

    Validation Logic:
    1. Checks if the record is being edited (i.e., it has a previously published
       version with the same ID).
    2. If the record is being edited and the previous version had a DOI registered
       with the "datacite" provider:
        - Ensures that the current record's access level is not set to "restricted".
        - If the access level is "restricted", an error is raised or appended to
          the `errors` list, indicating that a record with a DOI from CDS cannot
          be restricted.
        - Returns a response indicating that only "datacite" is allowed as the DOI
          provider for this version.
    3. If the record is not being edited or does not meet the above conditions:
        - Returns a response allowing multiple DOI providers: "external",
          "not_needed", and "datacite".

    Raises:
        ValidationErrorWithMessageAsList: If validation fails and the `errors`
        argument is not provided.
    """
    record_is_edited = (
        previous_published_record is not None
        and current_draft["id"] == previous_published_record["id"]
    )
    if record_is_edited:
        # We are editing a record that was already published
        if (
            previous_published_record.get("pids", {}).get("doi", {}).get("client", "")
            == "datacite"
        ):
            # The previous published record had a DOI
            if current_draft["access"]["record"] == "restricted":
                error_message = {
                    "field": "pids.doi",
                    "messages": [
                        _(
                            "This record’s DOI was registered with CDS and its metadata has been shared with Datacite,"
                            " so the record can’t be restricted. Please change the visibility to Public (or Public with restricted files)."
                        )
                    ],
                }
                if errors is not None:
                    errors.append(error_message)
                else:
                    raise ValidationErrorWithMessageAsList(message=[error_message])
            return dict(
                allowed_providers=["datacite"],
                message="The published record has already a DOI registered from CDS.",
            )

    return dict(
        allowed_providers=["external", "not_needed", "datacite"],
        message="",
    )
