# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""CDS-RDM exceptions."""

from flask_principal import identity_loaded

from .oidc import load_user_role_needs


class CDS_RDM_App(object):
    """CDS-RDM App."""

    def __init__(self, app):
        """Constructor."""
        self.app = app

        @identity_loaded.connect_via(app)
        def on_identity_loaded(_, identity):
            load_user_role_needs(identity)


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
