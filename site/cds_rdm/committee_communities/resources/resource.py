# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Committee approval communities resource."""

from flask import g
from flask_resources import Resource, resource_requestctx, response_handler, route
from invenio_records_resources.resources.records.resource import (
    request_data,
    request_search_args,
    request_view_args,
)

from .errors import ErrorHandlersMixin


class CommitteeCommunityResource(ErrorHandlersMixin, Resource):
    """Committee approval communities resource."""

    def __init__(self, config, service):
        """Constructor."""
        super().__init__(config)
        self.service = service

    def create_url_rules(self):
        """Create the URL rules."""
        routes = self.config.routes
        return [
            route("GET", routes["list"], self.search),
            route("POST", routes["list"], self.create),
            route("GET", routes["item"], self.read),
            route("PUT", routes["item"], self.update),
            route("DELETE", routes["item"], self.delete),
        ]

    @request_search_args
    @response_handler(many=True)
    def search(self):
        """Search entries."""
        items = self.service.search(g.identity, params=resource_requestctx.args)
        return items.to_dict(), 200

    @request_data
    @response_handler()
    def create(self):
        """Create an entry."""
        item = self.service.create(g.identity, resource_requestctx.data or {})
        return item.to_dict(), 201

    @request_view_args
    @response_handler()
    def read(self):
        """Read an entry."""
        item = self.service.read(g.identity, resource_requestctx.view_args["item_id"])
        return item.to_dict(), 200

    @request_view_args
    @request_data
    @response_handler()
    def update(self):
        """Update an entry."""
        item = self.service.update(
            g.identity,
            resource_requestctx.view_args["item_id"],
            resource_requestctx.data or {},
        )
        return item.to_dict(), 200

    @request_view_args
    def delete(self):
        """Delete an entry."""
        self.service.delete(g.identity, resource_requestctx.view_args["item_id"])
        return "", 204
