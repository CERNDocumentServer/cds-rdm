# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2023 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Permission policy."""

from invenio_communities.permissions import CommunityPermissionPolicy
from invenio_rdm_records.services.permissions import RDMRecordPermissionPolicy
from .generators import CERNEmailsGroups, Archiver
from invenio_records_permissions.generators import (
    SystemProcess,
)
from invenio_users_resources.services.permissions import UserManager

from invenio_rdm_records.services.generators import IfRecordDeleted


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


class CDSRDMRecordPermissionPolicy(RDMRecordPermissionPolicy):
    can_view = RDMRecordPermissionPolicy.can_view
    can_read = RDMRecordPermissionPolicy.can_read + [Archiver()]
    can_search = RDMRecordPermissionPolicy.can_search + [Archiver()]
    can_read_files = RDMRecordPermissionPolicy.can_read_files + [Archiver()]
    can_get_content_files = RDMRecordPermissionPolicy.can_get_content_files + [
        Archiver()
    ]
    can_media_get_content_files = RDMRecordPermissionPolicy.can_get_content_files + [
        Archiver()
    ]
    can_read_deleted = [
        IfRecordDeleted(
            then_=[UserManager, SystemProcess()],
            else_=can_read + [Archiver()],
        )
    ]
