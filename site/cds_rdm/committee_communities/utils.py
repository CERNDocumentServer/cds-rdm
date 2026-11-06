# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Committee approval communities utilities."""

from flask import g, has_request_context

from .models import CommitteeApprovalCommunity

_CACHE_ATTR = "_cds_committee_approval_community"


def _load_community(community_id):
    try:
        return CommitteeApprovalCommunity.get_by_community_id(community_id)
    except (ValueError, AttributeError):  # malformed UUID
        return None


def get_committee_approval_enrollment(community_id):
    """Return the ``CommitteeApprovalCommunity`` entry, or ``None``.

    ``None`` means the community is not enrolled in the committee approval
    workflow. The lookup is cached for the duration of a request.
    """
    if not community_id:
        return None
    community_id = str(community_id)
    if not has_request_context():
        return _load_community(community_id)
    cache = g.setdefault(_CACHE_ATTR, {})
    if community_id not in cache:
        cache[community_id] = _load_community(community_id)
    return cache[community_id]


def get_report_number_prefixes():
    """Return the report number prefixes of all enrolled communities."""
    return CommitteeApprovalCommunity.get_report_number_prefixes()
