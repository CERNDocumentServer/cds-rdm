# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Committee approval communities permissions."""

from invenio_administration.generators import Administration
from invenio_records_permissions import BasePermissionPolicy
from invenio_records_permissions.generators import SystemProcess


class CommitteeCommunityPermissionPolicy(BasePermissionPolicy):
    """Only administrators (``administration-access``) can manage entries."""

    can_create = [Administration(), SystemProcess()]
    can_read = [Administration(), SystemProcess()]
    can_search = [Administration(), SystemProcess()]
    can_update = [Administration(), SystemProcess()]
    can_delete = [Administration(), SystemProcess()]
