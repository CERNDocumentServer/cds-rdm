# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2025 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""EP Approval state helpers for the record landing page."""

from flask import current_app, g
from invenio_access.permissions import system_identity
from invenio_communities.generators import CommunityRoleNeed
from invenio_pidstore.models import PersistentIdentifier
from invenio_rdm_records.records.api import RDMRecord
from invenio_requests.proxies import current_requests_service


def _get_apprn_public_record_state(metadata, custom_fields=None):
    """Return state dict for a public EP-approved record, or None.

    A record is the "public approved copy" when its metadata.identifiers contains
    an entry with scheme="apprn" AND cern:committee_approval.internally_reviewed_id
    is set (linking back to the internal draft).

    The approved draft also gets the apprn identifier (via CommitteeApprovalComponent),
    so apprn alone is not sufficient — the CF back-link is the distinguishing marker.

    Newer versions of the public record also inherit internally_reviewed_id via
    InvenioRDM's new_version copy.  The "Reviewed version" link is shown only on
    version v1 of the public record (handled in the frontend by checking item.version).
    """
    identifiers = metadata.get("identifiers", [])
    apprn_entry = next((i for i in identifiers if i.get("scheme") == "apprn"), None)
    if not apprn_entry:
        return None
    # Approved draft: has apprn but no internally_reviewed_id → not the public copy.
    _ca = (custom_fields or {}).get("cern:committee_approval") or {}
    draft_id = _ca.get("internally_reviewed_id")
    if not draft_id:
        return None
    return {
        "can_submit": False,
        "community_enrolled": False,
        "is_public_approved_record": True,
        "draft_record_id": draft_id,
        "approved_report_number": None,
        "public_record_id": None,
        "open_request": None,
        "receiver_group": None,
    }


def _get_enrolled_community(record_ui):
    """Return (community_id, community_config) for enrolled communities, else (None, None)."""
    ep_communities = current_app.config.get("CDS_EP_APPROVAL_COMMUNITIES", {})
    parent = record_ui.get("parent", {}) if record_ui else {}
    default_community_id = parent.get("communities", {}).get("default")
    config = ep_communities.get(default_community_id) if default_community_id else None
    return (default_community_id, config) if config else (None, None)


def _get_parent_recids(record_id):
    """Return all recids in the record's parent (version family) via DB lookup.

    Falls back to [record_id] if the lookup fails.
    """
    try:
        pid_obj = PersistentIdentifier.get("recid", record_id)
        rec_obj = RDMRecord.get_record(pid_obj.object_uuid)
        recids = []
        for rec in RDMRecord.get_records_by_parent(rec_obj.parent):
            pid = PersistentIdentifier.query.filter_by(
                pid_type="recid",
                object_uuid=str(rec.id),
                object_type="rec",
            ).first()
            if pid:
                recids.append(pid.pid_value)
        return recids or [record_id]
    except Exception:
        return [record_id]


def _get_parent_latest_request(record_id):
    """Return the most-recent EP approval request across the parent (any non-cancelled status).

    Covers submitted, declined, and accepted requests so the UI can disable
    re-submission and link to the request page.
    Note: the requests search schema does not expose the payload, so only
    id/status/links are returned here.  Approval data (report number, approved
    version) is sourced from the record CF via _get_parent_approval_cf instead.
    """
    try:
        parent_recids = _get_parent_recids(record_id)
        topic_query = " OR ".join(f'topic.record:"{r}"' for r in parent_recids)
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


def _get_parent_approval_cf(record_id):
    """Scan all versions in the parent for committee approval CF data.

    The CF is only written to the submitted version; newer versions that inherit
    it via new_version also carry it.  Pre-approval versions don't.
    Returns (approved_report_number, approved_version_recid) or (None, None).
    approved_version_recid is read from CF["version"] (the originally submitted
    recid) rather than the scanned record's own recid, so the badge always
    points to the specific version that was submitted for approval.
    """
    try:
        parent_recids = _get_parent_recids(record_id)
        for recid in parent_recids:
            pid_obj = PersistentIdentifier.get("recid", recid)
            rec = RDMRecord.get_record(pid_obj.object_uuid)
            _ca = (rec.get("custom_fields") or {}).get("cern:committee_approval") or {}
            rn = _ca.get("reportnumber")
            if rn:
                # CF["version"] is the originally submitted version's recid.
                submitted_recid = _ca.get("version") or recid
                return rn, submitted_recid
        return None, None
    except Exception:
        return None, None


def _check_can_submit(community_id):
    """Return True if the current user is a curator, manager, or owner of the community."""
    try:
        identity = g.identity
        return any(
            CommunityRoleNeed(community_id, role) in identity.provides
            for role in ("curator", "manager", "owner")
        )
    except Exception:
        return False


def _get_parent_public_info(record_id, current_cf):
    """Scan parent versions for public_record_id and identify the source version.

    public_record_id + public_source_recid are written exclusively to the source
    version by publish_public_record — so exactly one version in the family carries
    them.  Scanning each version's CF lets us expose public_record_id for any
    version in the family (guard / "view" link).

    Returns (public_record_id, public_source_recid) or (None, None).
    Fast-paths if the current record is the source.
    """
    # Fast path: the current version is the source.
    _ca = (current_cf or {}).get("cern:committee_approval") or {}
    local_id = _ca.get("public_record_id")
    if local_id:
        return local_id, record_id

    # Scan the parent family.
    try:
        parent_recids = _get_parent_recids(record_id)
        for recid in parent_recids:
            if recid == record_id:
                continue  # already checked above
            pid_obj = PersistentIdentifier.get("recid", recid)
            rec = RDMRecord.get_record(pid_obj.object_uuid)
            _fam_ca = (rec.get("custom_fields") or {}).get("cern:committee_approval") or {}
            pub_id = _fam_ca.get("public_record_id")
            if pub_id:
                return pub_id, recid
    except Exception:
        pass
    return None, None


def _get_versions_cf_map(record_id):
    """Return a dict mapping recid → relevant CF fields for every version in the family.

    Only includes versions that carry cern:committee_approval (approved version and
    post-approval versions).  Pre-approval versions have no CF and are omitted.

    Used by the frontend RecordVersionItem to render approval badges per-version
    without relying on which version is currently being viewed.
    """
    try:
        parent_recids = _get_parent_recids(record_id)
        result = {}
        for recid in parent_recids:
            pid_obj = PersistentIdentifier.get("recid", recid)
            rec = RDMRecord.get_record(pid_obj.object_uuid)
            _ca = (rec.get("custom_fields") or {}).get("cern:committee_approval") or {}
            if not _ca.get("reportnumber"):
                continue
            result[recid] = {
                "reportnumber": _ca.get("reportnumber"),
                "version": _ca.get("version"),
                "public_record_id": _ca.get("public_record_id"),
            }
        return result
    except Exception:
        return {}


def _check_can_create_public(can_submit, custom_fields, record_id):
    """Return True if this version may be used as the source for a public record.

    Requires:
    - can_submit is True (user is a manager/owner)
    - an approval number exists on this version
    - this version's index >= the approved version's index (no pre-approval versions)
    """
    if not can_submit:
        return False
    _ca = custom_fields.get("cern:committee_approval") or {}
    if not _ca.get("reportnumber"):
        return False
    approved_version_recid = _ca.get("version")
    if not approved_version_recid or approved_version_recid == record_id:
        return True
    try:
        appr_pid = PersistentIdentifier.get("recid", approved_version_recid)
        appr_rec = RDMRecord.get_record(appr_pid.object_uuid)
        cur_pid = PersistentIdentifier.get("recid", record_id)
        cur_rec = RDMRecord.get_record(cur_pid.object_uuid)
        return cur_rec.versions.index >= appr_rec.versions.index
    except Exception:
        return True  # fail open — backend will re-validate


def get_ep_approval_state(record_ui, record=None):
    """Return EP approval state for the record landing page.

    Returns a dict with:
      - can_submit: bool
      - can_create_public: bool
      - community_enrolled: bool
      - is_public_approved_record: bool
      - open_request: dict or None — {id, status, links}
      - approved_report_number: str or None
      - approval_date: str or None
      - approved_version: str or None
      - public_record_id: str or None
      - draft_record_id: str or None
      - receiver_group: str or None
    """
    metadata = record_ui.get("metadata", {}) if record_ui else {}
    custom_fields_top = record_ui.get("custom_fields", {}) if record_ui else {}

    # Early exit: this IS the public EP-approved copy.
    public_state = _get_apprn_public_record_state(metadata, custom_fields_top)
    if public_state is not None:
        return public_state

    # Check community enrollment.
    community_id, community_config = _get_enrolled_community(record_ui)
    if community_id is None:
        return {
            "can_submit": False,
            "community_enrolled": False,
            "is_public_approved_record": False,
            "open_request": None,
            "approved_report_number": None,
            "public_record_id": None,
            "receiver_group": None,
        }

    custom_fields = record_ui.get("custom_fields", {}) if record_ui else {}
    record_id = record_ui.get("id") if record_ui else None
    _ca = custom_fields.get("cern:committee_approval") or {}

    open_request = _get_parent_latest_request(record_id)
    can_submit = _check_can_submit(community_id)
    approved_report_number = _ca.get("reportnumber")
    approved_version = _ca.get("version")

    # For pre-approval versions (no CF on this record), scan the parent so the
    # "Approved as …" button and versions badge still appear correctly.
    if not approved_report_number:
        approved_report_number, approved_version = _get_parent_approval_cf(record_id)

    public_record_id, _ = _get_parent_public_info(record_id, custom_fields)
    can_create_public = _check_can_create_public(can_submit, custom_fields, record_id)
    versions_cf = _get_versions_cf_map(record_id)

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
        "approval_date": _ca.get("datetime"),
        "public_record_id": public_record_id,
        "versions_cf": versions_cf,
        "draft_record_id": None,
        "receiver_group": community_config.get("referee_group"),
        "cern_scientific_community_id": cern_scientific_community_id,
    }
