# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2023 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Additional views."""

from flask import Blueprint


#
# Registration
#
def create_blueprint(app):
    """Register blueprint routes on app."""
    blueprint = Blueprint(
        "cds_rdm",
        __name__,
        template_folder="./templates",
    )

    # Add URL rules
    return blueprint
