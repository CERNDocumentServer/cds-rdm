# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Custom administration dashboard view."""

from functools import wraps

from flask import abort
from flask_principal import Permission, RoleNeed
from invenio_administration.permissions import administration_permission
from invenio_administration.views.dashboard import AdminDashboardView as BaseAdminDashboardView
from cds_rdm.permissions import can_access_administration_menu


def require_admin_or_harvester_curator(f):
    """Decorator to check if user has admin or harvester-curator permission."""
    @wraps(f)
    def decorated_view(*args, **kwargs):
        # Check standard administration permission
        if administration_permission.can():
            return f(*args, **kwargs)

        # Also allow harvester-curator role
        if Permission(RoleNeed("harvester-curator")).can():
            return f(*args, **kwargs)

        # No permission, return 403
        abort(403)

    return decorated_view


class CDSAdminDashboardView(BaseAdminDashboardView):
    """Custom dashboard view accessible by admin and harvester-curator."""

    decorators = [require_admin_or_harvester_curator]

    @staticmethod
    def visible_when():
        """Return a callable to check if dashboard menu should be visible."""
        return lambda: can_access_administration_menu()
