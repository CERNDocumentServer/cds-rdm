# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""CDS-RDM module."""
from cds_rdm.clc_sync.resources.config import CLCSyncResourceConfig
from cds_rdm.clc_sync.resources.resource import CLCSyncResource
from cds_rdm.clc_sync.services.config import CLCSyncServiceConfig
from cds_rdm.clc_sync.services.service import CLCSyncService

from . import config


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
