# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Jobs module."""

from datetime import timezone

from invenio_i18n import gettext as _
from invenio_vocabularies.jobs import ProcessDataStreamJob
from marshmallow import Schema, ValidationError, fields, validates_schema
from marshmallow_utils.fields import TZDateTime


class InspireArgsSchema(Schema):
    """Schema of task input arguments."""

    since = TZDateTime(
        timezone=timezone.utc,
        format="%Y-%m-%d",
        allow_none=True,
        metadata={
            "description": _(
                "YYYY-MM-DD format. "
                "Leave field empty if it should continue since last successful run."
            )
        },
    )

    until = TZDateTime(
        timezone=timezone.utc,
        format="%Y-%m-%d",
        allow_none=True,
        metadata={
            "description": _(
                "YYYY-MM-DD format. "
                "End date of the date range. If this field is provided, then Since field is mandatory. Start/End date is included."
            )
        },
    )

    on = TZDateTime(
        timezone=timezone.utc,
        format="%Y-%m-%d",
        allow_none=True,
        metadata={"description": _("YYYY-MM-DD format. Harvest by exact date.")},
    )

    inspire_id = fields.String(allow_none=True)

    job_arg_schema = fields.String(
        metadata={"type": "hidden"},
        dump_default="InspireArgsSchema",
        load_default="InspireArgsSchema",
    )

    @validates_schema
    def validate_date_range(self, data, **kwargs):
        """Ensure that since <= until."""
        since = data.get("since")
        until = data.get("until")

        if since and until and since > until:
            raise ValidationError(
                _("The 'Since' date must be earlier than or equal to the 'Until' date.")
            )

    @validates_schema
    def validate_exclusive_arguments(self, data, **kwargs):
        """Ensures that the user provides valid combinations of parameters."""
        inspire_id = data.get("inspire_id")
        on = data.get("on")
        since = data.get("since")
        until = data.get("until")

        # if `inspire_id` is provided, no other fields should be present
        if inspire_id and any([on, since, until]):
            raise ValidationError(
                _(
                    "When providing INSPIRE record ID for the search, all other args ('On', 'Since' and "
                    "'Until') are ignored. Please specify only inspire_id value."
                )
            )

        # if `on` is provided, no other fields should be present
        if on and any([inspire_id, since, until]):
            raise ValidationError(
                _(
                    "When searching by exact date, all other args ('Inspire_id', 'Since' and "
                    "'Until') are ignored. Please specify only 'On' value."
                )
            )

        # if `until` is provided, `since` must also be present
        if until and since is None:
            raise ValidationError(
                _(
                    "Only end date of the date range ('Until') is provided. Please also specify the 'Since' parameter."
                )
            )


class ProcessInspireHarvesterJob(ProcessDataStreamJob):
    """Process INSPIRE to CDS harvester registered task."""

    description = "Inspire to CDS records harvester"
    title = "Inspire harvester"
    id = "process_inspire"
    arguments_schema = InspireArgsSchema

    @classmethod
    def build_task_arguments(
        cls, job_obj, since=None, inspire_id=None, until=None, on=None, **kwargs
    ):
        """Build task arguments."""
        reader_args = {
            "since": since,
            "until": until,
            "on": on,
            "inspire_id": inspire_id,
        }
        # validate args
        InspireArgsSchema().load(data=reader_args)

        return {
            "config": {
                "readers": [
                    {
                        "args": reader_args,
                        "type": "inspire-http-reader",
                    },
                ],
                "writers": [
                    {
                        "args": {
                            "writer": {
                                "type": "TODO",
                                "args": {},
                            }
                        },
                        "type": "async",
                    }
                ],
                "transformers": [{"type": "inspire-json-transformer"}],
            }
        }
