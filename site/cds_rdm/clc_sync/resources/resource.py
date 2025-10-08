# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""CLC Sync module to create REST APIs."""

from flask import g
from flask_resources import Resource, resource_requestctx, response_handler, route
from invenio_records_resources.resources.records.resource import (
    request_data,
    request_headers,
    request_search_args,
    request_view_args,
)

from .errors import ErrorHandlersMixin


#
# Resource
#
class CLCSyncResource(ErrorHandlersMixin, Resource):
    """Banner resource."""

    def __init__(self, config, service):
        """Constructor."""
        super(CLCSyncResource, self).__init__(config)
        self.service = service

    def create_url_rules(self):
        """Create the URL rules for the record resource."""
        routes = self.config.routes
        return [
            route("POST", routes["list"], self.create),
            route("GET", routes["item"], self.read),
            route("GET", routes["list"], self.search),
            route("DELETE", routes["item"], self.delete),
            route("PUT", routes["item"], self.update),
        ]

    @request_view_args
    @request_data
    @response_handler()
    def update(self):
        """Update a CLC sync entry."""
        clc_sync = self.service.update(
            id=resource_requestctx.view_args["record_pid"],
            identity=g.identity,
            data=resource_requestctx.data,
        )

        return clc_sync.to_dict(), 200

    @request_view_args
    @response_handler()
    def read(self):
        """Read a sync entry."""
        record_pid = resource_requestctx.view_args["record_pid"]
        clc_sync = self.service.read(
            id=record_pid,
            identity=g.identity,
        )

        return clc_sync.to_dict(), 200

    @request_search_args
    @response_handler(many=True)
    def search(self):
        """Perform a search over the sync entries."""
        clc_sync_entries = self.service.search(
            identity=g.identity,
            params=resource_requestctx.args,
        )
        return clc_sync_entries.to_dict(), 200

    @request_data
    @response_handler()
    def create(self):
        """Create a sync entry."""
        clc_sync = self.service.create(
            g.identity,
            resource_requestctx.data or {},
        )

        return clc_sync.to_dict(), 201

    @request_headers
    @request_view_args
    def delete(self):
        """Delete a sync entry."""
        record_pid = resource_requestctx.view_args["record_pid"]
        clc_sync = self.service.delete(
            id=record_pid,
            identity=g.identity,
        )

        return clc_sync.to_dict(), 204
