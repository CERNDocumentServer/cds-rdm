# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Integration tests for the Committee Approval workflow."""

from datetime import date

import pytest
from flask_principal import RoleNeed
from invenio_access.permissions import system_identity
from invenio_communities.generators import CommunityRoleNeed
from invenio_db import db
from invenio_pidstore.models import PersistentIdentifier, PIDStatus
from invenio_rdm_records.proxies import current_rdm_records
from invenio_rdm_records.records.api import RDMRecord
from invenio_records_resources.services.errors import (
    PermissionDeniedError,
    RecordPermissionDeniedError,
)
from invenio_requests.proxies import (
    current_request_type_registry,
    current_requests_service,
)
from invenio_users_resources.records.api import UserAggregate
from marshmallow import ValidationError

from cds_rdm.generators import (
    COMMITTEE_APPROVAL_GRANT_ORIGIN_PREFIX,
    COMMITTEE_APPROVAL_GRANT_PERMISSION,
)
from cds_rdm.requests.committee_approval import (
    APPRN_PID_TYPE,
    CommitteeApprovalAcceptAction,
)
from cds_rdm.schemes import is_approval_report_number

from .conftest import _publish_record_in_community

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

YEAR = date.today().year
EP_RN_CONFIG = {"prefix": "CERN-EP", "include_year": True, "counter_digits": 3}
TH_RN_CONFIG = {"prefix": "CERN-TH", "include_year": True, "counter_digits": 3}
EP_GROUP_NAME = "cds-ph-ep-publication"


# ---------------------------------------------------------------------------
# Local fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def ep_referee_group(app, db):
    """Create the EP referee role/group in the DB."""
    ds = app.extensions["invenio-accounts"].datastore
    role = ds.create_role(
        id=EP_GROUP_NAME,
        name=EP_GROUP_NAME,
        description="EP publication committee",
    )
    db.session.commit()
    return role


@pytest.fixture()
def ep_request_payload():
    """Minimal valid EP approval request payload."""
    return {
        "payload": {
            "experiment": "ATLAS",
            "submitted_by": "Jane Doe",
            "role": "Author",
            "publication_title": "Search for new physics at the LHC",
        }
    }


@pytest.fixture()
def ep_referee(UserFixture, ep_referee_group, app, db):
    """A user that is a member of the EP referee group.

    The RoleNeed is injected directly — going through the full group membership
    flow is out of scope for these tests.
    """

    u = UserFixture(
        email="ep-referee@inveniosoftware.org",
        password="ep-referee",
        preferences={
            "visibility": "public",
            "email_visibility": "restricted",
            "notifications": {"enabled": True},
        },
        active=True,
        confirmed=True,
    )
    u.create(app, db)
    UserAggregate.index.refresh()

    u.identity.provides.add(RoleNeed(EP_GROUP_NAME))
    return u


@pytest.fixture()
def community_manager(UserFixture, committee_enrolled_community, app, db):
    """A user with community-manager role in the EP-enrolled community.

    The CommunityRoleNeed is injected directly into the identity because
    user membership goes through invite→accept (out of scope here).
    """
    u = UserFixture(
        email="ep-manager@inveniosoftware.org",
        password="ep-manager",
        preferences={
            "visibility": "public",
            "email_visibility": "restricted",
            "notifications": {"enabled": True},
        },
        active=True,
        confirmed=True,
    )
    u.create(app, db)
    UserAggregate.index.refresh()
    u.identity.provides.add(
        CommunityRoleNeed(str(committee_enrolled_community.id), "manager")
    )
    return u


# ---------------------------------------------------------------------------
# Scheme validator tests (pure unit)
# ---------------------------------------------------------------------------


def test_approval_rn_valid_ep_format():
    """Standard CERN-EP format validates correctly."""
    assert is_approval_report_number(f"CERN-EP-{YEAR}-001")
    assert is_approval_report_number(f"CERN-EP-{YEAR}-42")
    assert is_approval_report_number(f"CERN-EP-{YEAR}-999")


def test_approval_rn_valid_th_format():
    """Theory department format validates correctly."""
    assert is_approval_report_number(f"CERN-TH-{YEAR}-001")
    assert is_approval_report_number("CERN-TH-2099-100")


def test_approval_rn_invalid_formats():
    """Various invalid formats are rejected."""
    assert not is_approval_report_number(f"cern-ep-{YEAR}-001")  # lowercase
    assert not is_approval_report_number("CERN-EP-26-001")  # 2-digit year
    assert not is_approval_report_number(f"CERN-EP-{YEAR}")  # missing seq
    assert not is_approval_report_number(f"{YEAR}-001")  # missing prefix
    assert not is_approval_report_number("")  # empty
    assert not is_approval_report_number(f"CERN-EP-{YEAR}-abc")  # non-numeric seq


# ---------------------------------------------------------------------------
# Request type registration
# ---------------------------------------------------------------------------


def test_committee_approval_request_type_is_registered(app):
    """CommitteeApprovalRequest must be discoverable via the request type registry."""
    request_type = current_request_type_registry.lookup(
        "committee-approval", quiet=True
    )
    assert request_type is not None
    assert request_type.type_id == "committee-approval"


# ---------------------------------------------------------------------------
# Report number generation
# ---------------------------------------------------------------------------


def test_generate_report_number_first_of_year(app, db):
    """First number minted in a year produces seq=1."""
    action = CommitteeApprovalAcceptAction.__new__(CommitteeApprovalAcceptAction)
    assert action._next_report_number(EP_RN_CONFIG) == f"CERN-EP-{YEAR}-001"


def test_generate_report_number_sequential_increment(app, db):
    """Each call increments the sequence based on existing PIDs."""
    action = CommitteeApprovalAcceptAction.__new__(CommitteeApprovalAcceptAction)
    prefix = f"CERN-EP-{YEAR}-"

    for seq in ("001", "002"):
        PersistentIdentifier.create(
            pid_type=APPRN_PID_TYPE,
            pid_value=f"{prefix}{seq}",
            object_type="rec",
            object_uuid="00000000-0000-0000-0000-000000000001",
            status=PIDStatus.REGISTERED,
        )
    db.session.commit()

    assert action._next_report_number(EP_RN_CONFIG) == f"CERN-EP-{YEAR}-003"


def test_generate_report_number_independent_prefix_counters(app, db):
    """EP and TH patterns use independent counters — no cross-contamination."""
    action = CommitteeApprovalAcceptAction.__new__(CommitteeApprovalAcceptAction)

    PersistentIdentifier.create(
        pid_type=APPRN_PID_TYPE,
        pid_value=f"CERN-EP-{YEAR}-001",
        object_type="rec",
        object_uuid="00000000-0000-0000-0000-000000000002",
        status=PIDStatus.REGISTERED,
    )
    db.session.commit()

    assert action._next_report_number(EP_RN_CONFIG) == f"CERN-EP-{YEAR}-002"
    assert action._next_report_number(TH_RN_CONFIG) == f"CERN-TH-{YEAR}-001"


# ---------------------------------------------------------------------------
# Full workflow: submit → accept (enrolled community)
# ---------------------------------------------------------------------------


def test_committee_approval_submit_accept_assigns_report_number(
    record_in_enrolled_community,
    community_manager,
    ep_referee,
    ep_request_payload,
    app,
    db,
):
    """Submit → accept: report number is auto-generated and stored on the request."""
    request_type = current_request_type_registry.lookup("committee-approval")

    request = current_requests_service.create(
        identity=community_manager.identity,
        data=ep_request_payload,
        request_type=request_type,
        receiver={"group": EP_GROUP_NAME},
        topic={"record": record_in_enrolled_community.id},
    )

    assert request.data["status"] == "submitted"

    accepted = current_requests_service.execute_action(
        identity=ep_referee.identity,
        id_=request.id,
        action="accept",
        data={"payload": {"content": "<p>.</p>", "format": "html"}},
    )

    assert accepted.data["status"] == "accepted"
    report_number = accepted.data["payload"]["approved_report_number"]
    assert report_number == f"CERN-EP-{YEAR}-001"

    pid = PersistentIdentifier.query.filter_by(
        pid_type=APPRN_PID_TYPE, pid_value=report_number
    ).one()
    assert str(pid.object_uuid) == str(record_in_enrolled_community._record.id)


def test_committee_approval_second_request_increments_sequence(
    record_in_enrolled_community,
    community_manager,
    ep_referee,
    ep_request_payload,
    committee_enrolled_community,
    minimal_restricted_record,
    app,
    db,
):
    """A second accepted request gets the next sequential report number."""
    request_type = current_request_type_registry.lookup("committee-approval")

    r1 = current_requests_service.create(
        identity=community_manager.identity,
        data=ep_request_payload,
        request_type=request_type,
        receiver={"group": EP_GROUP_NAME},
        topic={"record": record_in_enrolled_community.id},
    )
    current_requests_service.execute_action(
        identity=ep_referee.identity,
        id_=r1.id,
        action="accept",
        data={"payload": {"content": "<p>.</p>", "format": "html"}},
    )

    # Second record in the same enrolled community.

    service = current_rdm_records.records_service
    record2 = _publish_record_in_community(
        community_manager.identity,
        minimal_restricted_record,
        committee_enrolled_community,
        service,
    )

    r2 = current_requests_service.create(
        identity=community_manager.identity,
        data=ep_request_payload,
        request_type=request_type,
        receiver={"group": EP_GROUP_NAME},
        topic={"record": record2.id},
    )
    accepted2 = current_requests_service.execute_action(
        identity=ep_referee.identity,
        id_=r2.id,
        action="accept",
        data={"payload": {"content": "<p>.</p>", "format": "html"}},
    )

    assert accepted2.data["payload"]["approved_report_number"] == f"CERN-EP-{YEAR}-002"


# ---------------------------------------------------------------------------
# Full workflow: submit → decline (enrolled community)
# ---------------------------------------------------------------------------


def test_committee_approval_submit_decline(
    record_in_enrolled_community,
    community_manager,
    ep_referee,
    ep_request_payload,
    app,
    db,
):
    """Submit → decline: status is declined and no report number is issued."""
    request_type = current_request_type_registry.lookup("committee-approval")

    request = current_requests_service.create(
        identity=community_manager.identity,
        data=ep_request_payload,
        request_type=request_type,
        receiver={"group": EP_GROUP_NAME},
        topic={"record": record_in_enrolled_community.id},
    )
    assert request.data["status"] == "submitted"

    declined = current_requests_service.execute_action(
        identity=ep_referee.identity,
        id_=request.id,
        action="decline",
        data={"payload": {"content": "<p>.</p>", "format": "html"}},
    )

    assert declined.data["status"] == "declined"
    assert declined.data["payload"].get("approved_report_number") is None
    assert PersistentIdentifier.query.filter_by(pid_type=APPRN_PID_TYPE).count() == 0


# ---------------------------------------------------------------------------
# Community enrollment validation
# ---------------------------------------------------------------------------


def test_committee_approval_submit_raises_for_record_without_community(
    minimal_restricted_record, uploader, ep_referee_group, app, db
):
    """Submit raises ValidationError when the record belongs to no community."""
    service = current_rdm_records.records_service
    draft = service.create(uploader.identity, minimal_restricted_record)
    record = service.publish(uploader.identity, id_=draft.id)

    request_type = current_request_type_registry.lookup("committee-approval")
    with pytest.raises(ValidationError, match="not part of any community"):
        current_requests_service.create(
            identity=system_identity,
            data={
                "payload": {
                    "experiment": "OTHER",
                    "submitted_by": "Someone",
                    "role": "Author",
                    "publication_title": "A paper",
                }
            },
            request_type=request_type,
            receiver={"group": EP_GROUP_NAME},
            topic={"record": record.id},
        )


def test_committee_approval_submit_raises_for_non_enrolled_community(
    record_in_non_enrolled_community, uploader, ep_referee_group, app, db
):
    """Submit raises ValidationError when the record's community is not enrolled."""
    request_type = current_request_type_registry.lookup("committee-approval")
    with pytest.raises(
        ValidationError, match="not enrolled in the committee approval workflow"
    ):
        current_requests_service.create(
            identity=system_identity,
            data={
                "payload": {
                    "experiment": "OTHER",
                    "submitted_by": "Someone",
                    "role": "Author",
                    "publication_title": "A paper",
                }
            },
            request_type=request_type,
            receiver={"group": EP_GROUP_NAME},
            topic={"record": record_in_non_enrolled_community.id},
        )


# ---------------------------------------------------------------------------
# CommitteeApprovalComponent — apprn identifier derived from parent committee_approval
# ---------------------------------------------------------------------------


def test_apprn_migrated_single_record_flow(
    minimal_restricted_record, uploader, app, db
):
    """Migration case: apprn persists on a single record across edit/publish cycles.

    migrate_cdsrn_to_apprn.py sets source_internal_version = own recid on the
    parent, which is the sentinel CommitteeApprovalComponent uses to decide
    whether to keep the apprn identifier.  Without it the identifier would be
    stripped on the next publish.
    """
    service = current_rdm_records.records_service
    report_number = f"CERN-EP-{YEAR}-001"

    draft = service.create(uploader.identity, minimal_restricted_record)
    record = service.publish(uploader.identity, id_=draft.id)

    # Simulate what migrate_cdsrn_to_apprn.py writes on the parent.
    # source_internal_version = own recid because there is no separate public copy.
    pid_obj = PersistentIdentifier.get("recid", record.id)
    rec_obj = RDMRecord.get_record(pid_obj.object_uuid)
    pf = rec_obj.parent.get("permission_flags") or {}
    pf["committee_approval"] = {
        "reportnumber": report_number,
        "approved_internal_version": record.id,
        "source_internal_version": record.id,
    }
    rec_obj.parent["permission_flags"] = pf
    rec_obj.parent.commit()
    db.session.commit()

    # First edit+publish: apprn must appear.
    sys_draft = service.edit(system_identity, id_=record.id)
    record = service.publish(system_identity, id_=sys_draft.id)
    apprn_ids = [
        i
        for i in record.data.get("metadata", {}).get("identifiers", [])
        if i.get("scheme") == "apprn"
    ]
    assert len(apprn_ids) == 1 and apprn_ids[0]["identifier"] == report_number

    # Second edit+publish: apprn must persist across further metadata edits.
    sys_draft2 = service.edit(system_identity, id_=record.id)
    record2 = service.publish(system_identity, id_=sys_draft2.id)
    apprn_ids2 = [
        i
        for i in record2.data.get("metadata", {}).get("identifiers", [])
        if i.get("scheme") == "apprn"
    ]
    assert len(apprn_ids2) == 1 and apprn_ids2[0]["identifier"] == report_number


def test_apprn_two_record_flow(minimal_restricted_record, uploader, app, db):
    """Two-record flow: apprn lives only on the public copy, never on the internal record.

    After committee approval the internal parent has approved_internal_version but
    NOT source_internal_version, so CommitteeApprovalComponent._should_sync_apprn
    returns False and apprn is never added — whether or not a public copy exists yet.

    The public copy gets source_internal_version from views.py, so it carries apprn.
    """
    service = current_rdm_records.records_service
    report_number = f"CERN-EP-{YEAR}-002"

    # Create and publish the internal record.
    draft = service.create(uploader.identity, minimal_restricted_record)
    internal = service.publish(uploader.identity, id_=draft.id)

    internal_pid = PersistentIdentifier.get("recid", internal.id)
    internal_rec_obj = RDMRecord.get_record(internal_pid.object_uuid)

    # After committee approval: approved_internal_version set, no source_internal_version.
    pf = internal_rec_obj.parent.get("permission_flags") or {}
    pf["committee_approval"] = {
        "reportnumber": report_number,
        "approved_internal_version": internal.id,
    }
    internal_rec_obj.parent["permission_flags"] = pf
    internal_rec_obj.parent.commit()
    db.session.commit()

    # Edit+publish internal before public record exists: apprn must NOT appear.
    sys_draft = service.edit(system_identity, id_=internal.id)
    internal_v2 = service.publish(system_identity, id_=sys_draft.id)
    apprn_ids = [
        i
        for i in internal_v2.data.get("metadata", {}).get("identifiers", [])
        if i.get("scheme") == "apprn"
    ]
    assert apprn_ids == []

    # After public record is created views.py writes approved_public_version back.
    # Internal record still must not carry apprn.
    pf["committee_approval"] = {
        "reportnumber": report_number,
        "approved_internal_version": internal.id,
        "approved_public_version": "9999999",
    }
    internal_rec_obj.parent["permission_flags"] = pf
    internal_rec_obj.parent.commit()
    db.session.commit()

    sys_draft2 = service.edit(system_identity, id_=internal.id)
    internal_v3 = service.publish(system_identity, id_=sys_draft2.id)
    apprn_ids2 = [
        i
        for i in internal_v3.data.get("metadata", {}).get("identifiers", [])
        if i.get("scheme") == "apprn"
    ]
    assert apprn_ids2 == []

    # Create the public copy with source_internal_version set (as views.py does).
    pub_draft = service.create(uploader.identity, minimal_restricted_record)
    public = service.publish(uploader.identity, id_=pub_draft.id)

    public_pid = PersistentIdentifier.get("recid", public.id)
    public_rec_obj = RDMRecord.get_record(public_pid.object_uuid)
    pf2 = public_rec_obj.parent.get("permission_flags") or {}
    pf2["committee_approval"] = {
        "reportnumber": report_number,
        "source_internal_version": internal.id,
    }
    public_rec_obj.parent["permission_flags"] = pf2
    public_rec_obj.parent.commit()
    db.session.commit()

    sys_draft3 = service.edit(system_identity, id_=public.id)
    public_v2 = service.publish(system_identity, id_=sys_draft3.id)
    apprn_ids3 = [
        i
        for i in public_v2.data.get("metadata", {}).get("identifiers", [])
        if i.get("scheme") == "apprn"
    ]
    assert len(apprn_ids3) == 1 and apprn_ids3[0]["identifier"] == report_number


# ---------------------------------------------------------------------------
# Permissions: who can submit an EP approval request
# ---------------------------------------------------------------------------


def test_committee_approval_submit_permissions(
    record_in_enrolled_community,
    uploader,
    ep_referee_group,
    ep_request_payload,
    committee_enrolled_community,
    app,
    db,
):
    """Only community managers/owners of enrolled communities can submit."""
    request_type = current_request_type_registry.lookup("committee-approval")

    # Plain uploader (reader, not manager) — must be denied.
    with pytest.raises(PermissionDeniedError):
        current_requests_service.create(
            identity=uploader.identity,
            data=ep_request_payload,
            request_type=request_type,
            receiver={"group": EP_GROUP_NAME},
            topic={"record": record_in_enrolled_community.id},
        )

    # Simulate the uploader being a community manager by injecting the need
    # directly into the identity. members.add is groups-only; user membership
    # goes through invite→accept which is out of scope for this permission test.

    community_id = str(committee_enrolled_community.id)
    uploader.identity.provides.add(CommunityRoleNeed(community_id, "manager"))

    # Now as manager the uploader must be allowed.
    request = current_requests_service.create(
        identity=uploader.identity,
        data=ep_request_payload,
        request_type=request_type,
        receiver={"group": EP_GROUP_NAME},
        topic={"record": record_in_enrolled_community.id},
    )
    assert request.data["status"] == "submitted"


# ---------------------------------------------------------------------------
# Referee access grants — version scoping
# ---------------------------------------------------------------------------


def test_referee_grant_added_on_submit_removed_on_decline(
    record_in_enrolled_community,
    community_manager,
    ep_referee,
    ep_request_payload,
    app,
    db,
):
    """Submit adds a committee-review grant; decline removes it."""

    request_type = current_request_type_registry.lookup("committee-approval")

    pid_obj = PersistentIdentifier.get("recid", record_in_enrolled_community.id)
    record_uuid = pid_obj.object_uuid
    expected_origin = f"{COMMITTEE_APPROVAL_GRANT_ORIGIN_PREFIX}{record_uuid}"

    request = current_requests_service.create(
        identity=community_manager.identity,
        data=ep_request_payload,
        request_type=request_type,
        receiver={"group": EP_GROUP_NAME},
        topic={"record": record_in_enrolled_community.id},
    )

    # Grant must be present after submit.
    rec = RDMRecord.get_record(record_uuid)
    grants = [
        g
        for g in rec.parent.access.grants
        if g.permission == COMMITTEE_APPROVAL_GRANT_PERMISSION
        and g.origin == expected_origin
    ]
    assert len(grants) == 1
    assert grants[0].subject_id == EP_GROUP_NAME

    current_requests_service.execute_action(
        identity=ep_referee.identity,
        id_=request.id,
        action="decline",
        data={"payload": {"content": "<p>.</p>", "format": "html"}},
    )

    # Grant must be removed after decline.
    rec = RDMRecord.get_record(record_uuid)
    remaining = [
        g
        for g in rec.parent.access.grants
        if g.permission == COMMITTEE_APPROVAL_GRANT_PERMISSION
        and g.origin == expected_origin
    ]
    assert remaining == []


def test_referee_grant_retained_after_accept(
    record_in_enrolled_community,
    community_manager,
    ep_referee,
    ep_request_payload,
    app,
    db,
):
    """Accept keeps the grant so referees retain permanent access to the approved version."""

    request_type = current_request_type_registry.lookup("committee-approval")

    pid_obj = PersistentIdentifier.get("recid", record_in_enrolled_community.id)
    record_uuid = pid_obj.object_uuid
    expected_origin = f"{COMMITTEE_APPROVAL_GRANT_ORIGIN_PREFIX}{record_uuid}"

    request = current_requests_service.create(
        identity=community_manager.identity,
        data=ep_request_payload,
        request_type=request_type,
        receiver={"group": EP_GROUP_NAME},
        topic={"record": record_in_enrolled_community.id},
    )
    current_requests_service.execute_action(
        identity=ep_referee.identity,
        id_=request.id,
        action="accept",
        data={"payload": {"content": "<p>.</p>", "format": "html"}},
    )

    rec = RDMRecord.get_record(record_uuid)
    grants = [
        g
        for g in rec.parent.access.grants
        if g.permission == COMMITTEE_APPROVAL_GRANT_PERMISSION
        and g.origin == expected_origin
    ]
    assert len(grants) == 1


def test_referee_grant_scoped_to_submitted_version(
    record_in_enrolled_community,
    community_manager,
    ep_referee,
    ep_request_payload,
    app,
    db,
):
    """Referee can read the submitted version but not a new version created afterwards."""

    request_type = current_request_type_registry.lookup("committee-approval")
    service = current_rdm_records.records_service

    # Submit and accept the request for v1.
    request = current_requests_service.create(
        identity=community_manager.identity,
        data=ep_request_payload,
        request_type=request_type,
        receiver={"group": EP_GROUP_NAME},
        topic={"record": record_in_enrolled_community.id},
    )
    current_requests_service.execute_action(
        identity=ep_referee.identity,
        id_=request.id,
        action="accept",
        data={"payload": {"content": "<p>.</p>", "format": "html"}},
    )

    # Referee can read v1.
    v1 = service.read(identity=ep_referee.identity, id_=record_in_enrolled_community.id)
    assert v1.id == record_in_enrolled_community.id

    # Create v2.
    v2_draft = service.new_version(system_identity, id_=record_in_enrolled_community.id)
    v2 = service.publish(system_identity, id_=v2_draft.id)

    # Referee must NOT be able to read v2 — grant is scoped to v1's UUID.
    with pytest.raises(RecordPermissionDeniedError):
        service.read(identity=ep_referee.identity, id_=v2.id)
