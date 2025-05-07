# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""CLCSync resource config."""

import marshmallow as ma
from flask_resources import JSONDeserializer, RequestBodyParser
from invenio_records_resources.resources import RecordResourceConfig


class CLCSyncResourceConfig(RecordResourceConfig):
    """Banner resource config."""

    # Blueprint configuration
    blueprint_name = "clc-sync"
    url_prefix = "/clc"
    routes = {
        "item": "/<record_pid>",
        "list": "/",
    }

    request_view_args = {
        "record_pid": ma.fields.String(),
    }

    request_extra_args = {
        "url_path": ma.fields.String(),
    }

    request_body_parsers = {"application/json": RequestBodyParser(JSONDeserializer())}
    default_content_type = "application/json"

    response_handlers = {
        "application/vnd.inveniordm.v1+json": RecordResourceConfig.response_handlers[
            "application/json"
        ],
        **RecordResourceConfig.response_handlers,
    }
