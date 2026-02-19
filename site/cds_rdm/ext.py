# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the GPL-2.0 License; see LICENSE file for more details.

"""CDS-RDM module."""
from cds_rdm.clc_sync.resources.config import CLCSyncResourceConfig
from cds_rdm.clc_sync.resources.resource import CLCSyncResource
from cds_rdm.clc_sync.resources.utils import get_clc_sync_entry
from cds_rdm.clc_sync.services.config import CLCSyncServiceConfig
from cds_rdm.clc_sync.services.service import CLCSyncService
from cds_rdm.harvester_download.resources import (
    HarvesterDownloadResource,
    HarvesterDownloadResourceConfig,
)

from . import config
from .utils import evaluate_permissions
from .views import get_linked_records_search_query


class CDS_RDM_App(object):
    """CDS-RDM App."""

    def __init__(self, app):
        """Constructor."""
        if app:
            self.init_config(app)
            self.init_app(app)

    def init_config(self, app):
        """Initialize configuration."""
        for k in dir(config):
            app.config.setdefault(k, getattr(config, k))

    def init_app(self, app):
        """Flask application initialization."""
        self.init_services(app)
        self.init_resources(app)
        app.jinja_env.globals["get_clc_sync_entry"] = get_clc_sync_entry
        app.jinja_env.globals["evaluate_permissions"] = evaluate_permissions
        # Register filter for building linked records search query
        app.jinja_env.filters["get_linked_records_search_query"] = (
            get_linked_records_search_query
        )
        return app

    def init_services(self, app):
        """Initialize the services for banners."""
        self.clc_sync_service = CLCSyncService(config=CLCSyncServiceConfig)

    def init_resources(self, app):
        """Initialize the resources for banners."""
        self.clc_sync_resource = CLCSyncResource(
            service=self.clc_sync_service,
            config=CLCSyncResourceConfig,
        )
        self.harvester_download_resource = HarvesterDownloadResource(
            config=HarvesterDownloadResourceConfig,
        )


class CDS_RDM_UI(object):
    """CDS-RDM extension."""

    def __init__(self, app=None):
        """Extension initialization."""
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Flask application initialization."""
        extension = CDS_RDM_App(app)
        app.extensions["cds-rdm"] = extension
        return extension


class CDS_RDM_REST(object):
    """CDS-RDM REST extension."""

    def __init__(self, app=None):
        """Extension initialization."""
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Flask application initialization."""
        extension = CDS_RDM_App(app)
        app.extensions["cds-rdm"] = extension
        return extension
