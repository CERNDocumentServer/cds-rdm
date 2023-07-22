# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2023 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Permission policy."""

from invenio_communities.permissions import CommunityPermissionPolicy
from invenio_records_permissions.generators import SystemProcess

from .generators import CERNEmailsGroups


class CDSCommunitiesPermissionPolicy(CommunityPermissionPolicy):
    """Communities permission policy of CDS."""

    # for now, we want to restrict the creation of communities to admins
    can_create = [
        CERNEmailsGroups(
            config_key_emails="CDS_EMAILS_ALLOW_CREATE_COMMUNITIES",
            config_key_groups="CDS_GROUPS_ALLOW_CREATE_COMMUNITIES",
        ),
        SystemProcess(),
    ]
