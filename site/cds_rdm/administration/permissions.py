# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2026 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Permission policy."""
from invenio_access import Permission, action_factory

harvester_admin_access_action = action_factory("harvester-admin-access-action")
clc_sync_admin_access_action = action_factory("clc-sync-admin-access-action")

curators_permission = Permission(harvester_admin_access_action,
                                 clc_sync_admin_access_action)
