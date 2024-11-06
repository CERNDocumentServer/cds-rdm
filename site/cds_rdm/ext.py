# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""CDS-RDM module."""

from .authors.services import AuthorsService, AuthorsServiceConfig


class CDS_RDM_App(object):
    """CDS-RDM App."""

    def __init__(self, app):
        """Constructor."""
        self.app = app

    def service_configs(self, app):
        """Customized service configs."""

        class ServiceConfigs:
            authors = AuthorsServiceConfig

        return ServiceConfigs

    def init_services(self, app):
        """Initialize vocabulary resources."""
        service_configs = self.service_configs(app)

        # Services
        app.authors_service = AuthorsService(
            config=service_configs.authors,
        )

    def init_app(self, app):
        """Flask application initialization."""
        self.init_services(app)
        return app


class CDS_RDM_UI(object):
    """CDS-RDM extension."""

    def __init__(self, app=None):
        """Extension initialization."""
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Flask application initialization."""
        extension = CDS_RDM_App(app)
        extension.init_app(extension)
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
        extension.init_app(extension)
        app.extensions["cds-rdm"] = extension
        return extension
