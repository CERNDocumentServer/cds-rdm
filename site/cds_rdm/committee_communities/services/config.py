# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Committee approval communities service config."""

from invenio_records_resources.services import EndpointLink, RecordServiceConfig

from ..models import CommitteeApprovalCommunity
from .permissions import CommitteeCommunityPermissionPolicy
from .results import CommitteeCommunityItem, CommitteeCommunityList
from .schema import CommitteeApprovalCommunitySchema


class CommitteeCommunityServiceConfig(RecordServiceConfig):
    """Service configuration."""

    result_item_cls = CommitteeCommunityItem
    result_list_cls = CommitteeCommunityList
    permission_policy_cls = CommitteeCommunityPermissionPolicy
    schema = CommitteeApprovalCommunitySchema
    record_cls = CommitteeApprovalCommunity

    links_item = {
        "self": EndpointLink(
            "committee-communities.read",
            params=["item_id"],
            vars=lambda obj, vars: vars.update(item_id=str(obj.id)),
        ),
    }
