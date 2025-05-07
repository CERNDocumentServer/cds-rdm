# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Proxies for accessing the current Banners extension."""

from flask import current_app
from werkzeug.local import LocalProxy

current_cds_rdm = LocalProxy(lambda: current_app.extensions["cds-rdm"])
"""Proxy for the instantiated cds-rdm extension."""

current_clc_sync_service = LocalProxy(
    lambda: current_app.extensions["cds-rdm"].clc_sync_service
)
"""Proxy for the currently instantiated sync service."""
