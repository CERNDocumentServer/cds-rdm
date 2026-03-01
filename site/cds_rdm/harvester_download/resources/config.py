# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Harvester download resource config."""

from flask_resources import ResourceConfig


class HarvesterDownloadResourceConfig(ResourceConfig):
    """Harvester download resource config."""

    # Blueprint configuration
    blueprint_name = "harvester-download"
    url_prefix = "/harvester-reports"
    routes = {
        "download": "/download",
    }
