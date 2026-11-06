# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Committee approval communities service config."""

from invenio_records_resources.services import EndpointLink, RecordServiceConfig

from ..models import CommitteeApprovalEnrollment
from .permissions import CommitteeApprovalEnrollmentPermissionPolicy
from .results import CommitteeApprovalEnrollmentItem, CommitteeApprovalEnrollmentList
from .schema import CommitteeApprovalEnrollmentSchema


class CommitteeApprovalEnrollmentServiceConfig(RecordServiceConfig):
    """Service configuration."""

    result_item_cls = CommitteeApprovalEnrollmentItem
    result_list_cls = CommitteeApprovalEnrollmentList
    permission_policy_cls = CommitteeApprovalEnrollmentPermissionPolicy
    schema = CommitteeApprovalEnrollmentSchema
    record_cls = CommitteeApprovalEnrollment

    links_item = {
        "self": EndpointLink(
            "committee-approval-enrollments.read",
            params=["item_id"],
            vars=lambda obj, vars: vars.update(item_id=str(obj.id)),
        ),
    }
