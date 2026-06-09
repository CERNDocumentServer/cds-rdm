# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Harvester download resource."""

from datetime import datetime

from flask import Response, request
from flask_resources import HTTPJSONException, Resource, route

from cds_rdm.administration.permissions import curators_permission
from cds_rdm.harvester_runs.logs import (
    HarvesterRunError,
    fetch_harvester_run_logs,
    lines_from_hits,
    plain_text_log,
    resolve_harvester_run,
)


class HarvesterDownloadResource(Resource):
    """Harvester download resource."""

    def create_url_rules(self):
        """Create the URL rules for the download resource."""
        routes = self.config.routes
        return [
            route("GET", routes["download"], self.download),
        ]

    @staticmethod
    def _http_json_error(message, code):
        """Create a JSON HTTP error for REST responses."""
        return HTTPJSONException(code=code, description=message)

    def download(self):
        """Download a harvester run's logs as a plain-text ``.log`` file."""
        if not curators_permission.can():
            raise self._http_json_error("Permission denied", 403)

        try:
            run = resolve_harvester_run(request.args.get("run_id", ""))
        except HarvesterRunError as error:
            raise self._http_json_error(error.message, error.code)

        hits, total = fetch_harvester_run_logs(run)
        lines, error_count, warning_count = lines_from_hits(hits)
        logs = plain_text_log(run, lines, total, error_count, warning_count)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"harvester_logs_{run.id}_{timestamp}.log"

        return Response(
            logs,
            mimetype="text/plain",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
