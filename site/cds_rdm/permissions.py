# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2023 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Permission policy."""

from invenio_communities.permissions import CommunityPermissionPolicy
from invenio_preservation_sync.services.permissions import (
    DefaultPreservationInfoPermissionPolicy,
)
from invenio_rdm_records.services.generators import IfNewRecord, IfRecordDeleted
from invenio_rdm_records.services.permissions import RDMRecordPermissionPolicy
from invenio_records_permissions.generators import IfConfig, SystemProcess
from invenio_users_resources.services.permissions import UserManager

from .generators import Archiver, AuthenticatedRegularUser, CERNEmailsGroups


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
    """Record permission policy."""

    can_create = [AuthenticatedRegularUser(), SystemProcess()]
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

    can_manage_files = [
        IfConfig(
            "RDM_ALLOW_METADATA_ONLY_RECORDS",
            then_=[
                IfNewRecord(
                    then_=RDMRecordPermissionPolicy.can_authenticated,
                    else_=RDMRecordPermissionPolicy.can_review,
                )
            ],
            else_=[
                SystemProcess()
            ],  # needed for migrating records with no files as metadata-only
        ),
    ]


class CDSRDMPreservationSyncPermissionPolicy(DefaultPreservationInfoPermissionPolicy):
    """PreservationSync permission policy."""

    can_read = RDMRecordPermissionPolicy.can_read + [Archiver()]
    can_create = [Archiver()]
