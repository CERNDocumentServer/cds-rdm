# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2026 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""EP Approval state helpers for the record landing page."""

from flask import current_app, g
from invenio_access.permissions import system_identity
from invenio_communities.generators import CommunityRoleNeed
from invenio_requests.proxies import current_requests_service


def _get_enrolled_community(record_ui):
    """Return (community_id, community_config) for enrolled communities, else (None, None)."""
    ep_communities = current_app.config.get("CDS_EP_APPROVAL_COMMUNITIES", {})
    parent = record_ui.get("parent", {}) if record_ui else {}
    default_community_id = parent.get("communities", {}).get("default")
    config = ep_communities.get(default_community_id) if default_community_id else None
    return (default_community_id, config) if config else (None, None)


def _get_parent_ep_approval(record):
    """Read ep_approval dict directly from the parent record object.

    Returns the dict or {} if not set / record not available.
    """
    try:
        return (record._record.parent.get("permission_flags") or {}).get(
            "ep_approval"
        ) or {}
    except Exception:
        return {}


def _get_open_request(record_id, parent_record=None):
    """Return the most-recent EP approval request for the record family.

    Uses parent.get_records_by_parent to build the topic query so we cover
    all versions without a separate DB scan.
    """
    try:
        from invenio_pidstore.models import PersistentIdentifier
        from invenio_rdm_records.records.api import RDMRecord

        if parent_record is not None:
            recids = []
            for rec in RDMRecord.get_records_by_parent(parent_record):
                pid = PersistentIdentifier.query.filter_by(
                    pid_type="recid",
                    object_uuid=str(rec.id),
                    object_type="rec",
                ).first()
                if pid:
                    recids.append(pid.pid_value)
        else:
            recids = [record_id]

        topic_query = " OR ".join(
            f'topic.record:"{r}"' for r in (recids or [record_id])
        )
        results = current_requests_service.search(
            system_identity,
            params={
                "q": (
                    f'({topic_query}) AND type:"ep-approval"'
                    ' AND (status:"submitted" OR status:"declined" OR status:"accepted")'
                ),
                "size": 1,
                "sort": "newest",
            },
        )
        hits = list(results.hits)
        if not hits:
            return None
        req = hits[0]
        return {
            "id": req["id"],
            "status": req.get("status"),
            "links": req.get("links", {}),
        }
    except Exception:
        return None


def _check_can_curate_for_community(community_id):
    """Return True if the current user is a curator, manager, or owner of the community."""
    try:
        identity = g.identity
        return any(
            CommunityRoleNeed(community_id, role) in identity.provides
            for role in ("curator", "manager", "owner")
        )
    except Exception:
        return False


def _check_can_create_public(can_submit, ea, record_id):
    """Return True if this version may be used as the source for a public record.

    Requires:
    - can_submit is True (user is a manager/owner)
    - an approval number exists on the parent
    - this version's index >= the approved version's index
    - no public record has been created yet
    """
    if not can_submit:
        return False
    if not ea.get("reportnumber"):
        return False
    if ea.get("approved_public_version"):
        return False
    approved_version_recid = ea.get("approved_internal_version")
    if not approved_version_recid or approved_version_recid == record_id:
        return True
    try:
        from invenio_pidstore.models import PersistentIdentifier
        from invenio_rdm_records.records.api import RDMRecord

        appr_pid = PersistentIdentifier.get("recid", approved_version_recid)
        appr_rec = RDMRecord.get_record(appr_pid.object_uuid)
        cur_pid = PersistentIdentifier.get("recid", record_id)
        cur_rec = RDMRecord.get_record(cur_pid.object_uuid)
        return cur_rec.versions.index >= appr_rec.versions.index
    except Exception:
        return True  # fail open — backend will re-validate


def get_ep_approval_state(record_ui, record=None):
    """Return EP approval state for the record landing page.

    Reads ep_approval from the parent record object (single source of truth).
    No DB scans across versions needed.

    Returns a dict with:
      - can_submit: bool
      - can_create_public: bool
      - community_enrolled: bool
      - is_public_approved_record: bool
      - open_request: dict or None — {id, status, links}
      - approved_report_number: str or None
      - approval_date: str or None
      - ep_approval: dict — raw parent ep_approval (for frontend version badges)
      - draft_record_id: str or None
      - receiver_group: str or None
    """
    # Read ep_approval from the parent.
    ea = _get_parent_ep_approval(record)

    # Early exit: this IS the public EP-approved copy.
    # The public record's parent has source_internal_version set.
    if ea.get("source_internal_version"):
        default_community_id = (
            (record_ui or {}).get("parent", {}).get("communities", {}).get("default")
        )
        can_view_reviewed_version = (
            _check_can_curate_for_community(default_community_id)
            if default_community_id
            else False
        )
        return {
            "can_submit": False,
            "can_create_public": False,
            "community_enrolled": False,
            "is_public_approved_record": True,
            "open_request": None,
            "approved_report_number": ea.get("reportnumber"),
            "approval_date": None,
            "ep_approval": ea,
            "draft_record_id": ea["source_internal_version"],
            "can_view_reviewed_version": can_view_reviewed_version,
            "receiver_group": None,
            "cern_scientific_community_id": None,
        }

    # Check community enrollment.
    community_id, community_config = _get_enrolled_community(record_ui)
    if community_id is None:
        return {
            "can_submit": False,
            "can_create_public": False,
            "community_enrolled": False,
            "is_public_approved_record": False,
            "open_request": None,
            "approved_report_number": None,
            "approval_date": None,
            "ep_approval": {},
            "draft_record_id": None,
            "can_view_reviewed_version": False,
            "receiver_group": None,
        }

    record_id = record_ui.get("id") if record_ui else None

    # Get the parent object for the request search (avoids re-scanning recids).
    parent_record = None
    try:
        parent_record = record._record.parent
    except Exception:
        pass

    open_request = _get_open_request(record_id, parent_record)
    can_submit = _check_can_curate_for_community(community_id)
    approved_report_number = ea.get("reportnumber")
    can_create_public = _check_can_create_public(can_submit, ea, record_id)

    cern_scientific_community_id = current_app.config.get(
        "CDS_CERN_SCIENTIFIC_COMMUNITY_ID"
    )

    return {
        "can_submit": can_submit,
        "can_create_public": can_create_public,
        "community_enrolled": True,
        "is_public_approved_record": False,
        "open_request": open_request,
        "approved_report_number": approved_report_number,
        "approval_date": ea.get("datetime"),
        "ep_approval": ea,
        "draft_record_id": None,
        "can_view_reviewed_version": False,
        "receiver_group": community_config.get("referee_group"),
        "cern_scientific_community_id": cern_scientific_community_id,
    }
