# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Harvester download resource."""

from datetime import datetime

from flask import Response, g, request, stream_with_context
from flask_principal import Permission, RoleNeed
from flask_resources import Resource, route
from invenio_audit_logs.proxies import current_audit_logs_service


class HarvesterDownloadResource(Resource):
    """Harvester download resource."""

    def create_url_rules(self):
        """Create the URL rules for the download resource."""
        routes = self.config.routes
        return [
            route("GET", routes["download"], self.download),
        ]

    def download(self):
        """Download audit logs for harvester reports as plain text file."""
        permission = Permission(RoleNeed("harvester-curator"))
        if not permission.can():
            return {"message": "Permission denied"}, 403

        query = request.args.get("q", "")

        if not query:
            return {"message": "No query provided"}, 400

        params = {"q": query, "size": 1000}

        result = current_audit_logs_service.search(
            identity=g.identity,
            params=params,
        )

        def generate_logs():
            """Generate log lines one by one."""
            for hit in result.hits:
                timestamp = hit.get("created", "N/A")
                action = hit.get("action", "N/A")
                resource_type = hit.get("resource", {}).get("type", "N/A")
                resource_id = hit.get("resource", {}).get("id", "N/A")
                user_email = hit.get("user", {}).get("email", "N/A")

                # Format: [timestamp] action resource_type/resource_id user
                line = f"[{timestamp}] {action} {resource_type}/{resource_id} {user_email}\n"
                yield line

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"harvester_logs_{timestamp}.txt"

        return Response(
            stream_with_context(generate_logs()),
            mimetype="text/plain",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
