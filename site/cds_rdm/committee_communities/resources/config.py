# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Committee approval communities resource config."""

import marshmallow as ma
from flask_resources import JSONDeserializer, RequestBodyParser
from invenio_records_resources.resources import RecordResourceConfig


class CommitteeCommunityResourceConfig(RecordResourceConfig):
    """Resource configuration."""

    blueprint_name = "committee-communities"
    url_prefix = "/committee-communities"
    routes = {
        "item": "/<item_id>",
        "list": "/",
    }

    request_view_args = {"item_id": ma.fields.String()}
    request_body_parsers = {"application/json": RequestBodyParser(JSONDeserializer())}
    default_content_type = "application/json"

    response_handlers = {
        "application/vnd.inveniordm.v1+json": RecordResourceConfig.response_handlers[
            "application/json"
        ],
        **RecordResourceConfig.response_handlers,
    }
