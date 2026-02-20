# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""CLCSync permissions."""

from invenio_administration.generators import Administration
from invenio_records_permissions import BasePermissionPolicy
from invenio_records_permissions.generators import AnyUser, SystemProcess

from cds_rdm.permissions import Librarian


class CLCSyncPermissionPolicy(BasePermissionPolicy):
    """Permission policy for CLCSync."""

    can_create = [Librarian(), Administration(), SystemProcess()]
    can_read = [AnyUser(), SystemProcess()]
    can_search = [Librarian(), Administration(), SystemProcess()]
    can_update = [Librarian(), Administration(), SystemProcess()]
    can_delete = [Librarian(), Administration(), SystemProcess()]
