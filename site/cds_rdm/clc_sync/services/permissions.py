# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""CLCSync permissions."""

from invenio_access import action_factory
from invenio_access.permissions import Permission
from invenio_administration.generators import Administration
from invenio_records_permissions import BasePermissionPolicy
from invenio_records_permissions.generators import (
    AnyUser,
    Generator,
    SystemProcess,
)

clc_sync_action = action_factory("clc-sync-action")
clc_sync_permission = Permission(clc_sync_action)


class CLCExporter(Generator):
    """Allows administration-access."""

    def __init__(self):
        """Constructor."""
        super(CLCExporter, self).__init__()

    def needs(self, **kwargs):
        """Enabling Needs."""
        return [clc_sync_action]


class CLCSyncPermissionPolicy(BasePermissionPolicy):
    """Permission policy for CLCSync."""

    can_create = [CLCExporter(), Administration(), SystemProcess()]
    can_read = [AnyUser(), SystemProcess()]
    can_search = [CLCExporter(), Administration(), SystemProcess()]
    can_update = [CLCExporter(), Administration(), SystemProcess()]
    can_delete = [CLCExporter(), Administration(), SystemProcess()]
