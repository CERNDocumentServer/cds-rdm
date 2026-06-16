# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2025 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""EP Approval request type."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Final

from flask import current_app
from flask_principal import Identity
from invenio_access.permissions import system_identity
from invenio_db import db
from invenio_i18n import lazy_gettext as _
from invenio_notifications.services.uow import NotificationOp
from invenio_pidstore.models import PersistentIdentifier, PIDStatus
from invenio_rdm_records.records.api import RDMRecord
from invenio_rdm_records.requests.base import BaseRequest as RDMBaseRequest
from invenio_records_resources.services.errors import PermissionDeniedError
from invenio_records_resources.services.uow import UnitOfWork
from invenio_requests.customizations import actions
from invenio_requests.proxies import current_requests_service
from marshmallow import ValidationError, fields

from ..generators import EPWorkflowCommunityManager
from ..notifications.ep_approval import (
    EPApprovalAcceptNotificationBuilder,
    EPApprovalDeclineNotificationBuilder,
    EPApprovalSubmitNotificationBuilder,
)

# PID type stored in pidstore_pid.pid_type (VARCHAR(6) — keep ≤ 6 chars).
# The identifier scheme name in record metadata is "apprn" (no length limit).
# TODO: what is apprn? can we name this better?
APPRN_PID_TYPE = "apprn"


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


def _resolve_community_config(request):
    """Resolve the EP approval config for the request's topic record.

    Validates that:
    - the topic record belongs to at least one community, and
    - that community is enrolled in CDS_EP_APPROVAL_COMMUNITIES.

    Raises ``ValueError`` with a descriptive message if either condition fails.
    """
    topic = request.topic.resolve()
    default_community_id = topic.parent.get("communities", {}).get("default", "")
    if not default_community_id:
        raise ValidationError(
            "The record is not part of any community. "
            "It must belong to an EP-approval-enabled community before submitting."
        )
    ep_communities = current_app.config.get("CDS_EP_APPROVAL_COMMUNITIES", {})
    if default_community_id in ep_communities:
        return ep_communities[default_community_id]
    raise ValidationError(
        # TODO: do we need i18n for these errors?
        "The record's community is not enrolled in the EP approval workflow. "
        "Only records in EP-approval-enabled communities can be submitted."
    )


class EPApprovalSubmitAction(actions.CreateAndSubmitAction):
    """Submit action — validate community enrollment and notify referees."""

    def execute(self, identity: Identity, uow: UnitOfWork) -> None:
        """Execute submit: validate community, store version ID, notify referees."""
        # Enforce that only community managers of enrolled communities (or system)
        # can submit. The base service only checks generic can_create.
        topic = self.request.topic.resolve()
        is_system = identity.id == "system"
        allowed = is_system or any(
            need in identity.provides
            for need in EPWorkflowCommunityManager().needs(record=topic)
        )
        if not allowed:
            raise PermissionDeniedError()

        # Fail fast: ensure the record belongs to an enrolled community before
        # the request is persisted as submitted.
        _resolve_community_config(self.request)

        # Reject if the parent already carries an approval report number.
        if ((topic.parent.get("permission_flags") or {}).get("ep_approval") or {}).get(
            "reportnumber"
        ):
            raise ValidationError(
                "A version of this record already has an approval report number assigned. "
                "A new EP approval request cannot be submitted."
            )

        # Reject if there is already a submitted (pending) request for ANY version
        # in the family — prevents parallel submissions from older/newer versions.
        parent_recids = []
        for family_rec in RDMRecord.get_records_by_parent(topic.parent):
            pid = PersistentIdentifier.query.filter_by(
                pid_type="recid",
                object_uuid=str(family_rec.id),
                object_type="rec",
            ).first()
            if pid:
                parent_recids.append(pid.pid_value)
        parent_recids = parent_recids or [topic["id"]]

        topic_query = " OR ".join(f'topic.record:"{r}"' for r in parent_recids)
        existing = list(
            current_requests_service.search(
                system_identity,
                params={
                    "q": (
                        f'({topic_query}) AND type:"ep-approval"'
                        ' AND status:"submitted"'
                    ),
                    "size": 1,
                },
            ).hits
        )
        if existing:
            raise ValidationError(
                "An EP approval request is already pending for this record."
            )

        # Store the recid (pid_value) of the submitted version so that
        # _propagate_to_newer_versions can match it against search hit["id"].
        # The UUID (topic.id) is intentionally NOT stored here; it is resolved
        # at accept time directly from the request topic.
        # TODO: why do we need this
        self.request["payload"]["submitted_version_id"] = topic["id"]

        uow.register(
            NotificationOp(
                EPApprovalSubmitNotificationBuilder.build(
                    identity=identity,
                    request=self.request,
                )
            )
        )
        super().execute(identity, uow)


class EPApprovalAcceptAction(actions.AcceptAction):
    """Accept action — auto-generate the approval report number and assign it."""

    def _community_config(self):
        """Resolve the community config for this request (guaranteed enrolled at submit)."""
        return _resolve_community_config(self.request)

    def _generate_report_number(self, pattern: str) -> str:
        """Auto-generate the next sequential report number for the given pattern.

        Derives the next sequence number from the MAX existing apprn PID value
        for this pattern prefix and year, not a COUNT.  This is robust to gaps
        (deleted PIDs, failed accepts) — the sequence only ever goes forward.

        The prefix is extracted by splitting on ``{seq`` so that zero-padded
        formats like ``{seq:03d}`` do not produce a truncated prefix that misses
        PIDs >= 010 (e.g. "CERN-EP-2026-00" would miss "CERN-EP-2026-010").

        Pattern example: "CERN-EP-{year}-{seq:03d}"
        """
        year = date.today().year
        # Split on "{seq" to get everything before the sequence placeholder,
        # then format only the year part → "CERN-EP-2026-"
        # TODO: I don't understand what this is doing
        prefix = pattern.split("{seq")[0].format(year=year)
        existing = PersistentIdentifier.query.filter(
            PersistentIdentifier.pid_type == APPRN_PID_TYPE,
            PersistentIdentifier.pid_value.like(f"{prefix}%"),
        ).all()
        max_seq = max(
            (
                int(p.pid_value[len(prefix) :])
                for p in existing
                if p.pid_value[len(prefix) :].isdigit()
            ),
            default=0,
        )
        return pattern.format(year=year, seq=max_seq + 1)

    def _mint_apprn_pid(self, report_number: str, record_uuid: str) -> None:
        """Mint the apprn PID pointing at the given record UUID."""
        PersistentIdentifier.create(
            pid_type=APPRN_PID_TYPE,
            pid_value=report_number,
            object_type="rec",
            object_uuid=record_uuid,
            status=PIDStatus.REGISTERED,
        )

    def execute(self, identity: Identity, uow: UnitOfWork) -> None:
        """Execute accept: mint report number and write ep_approval to the parent.

        All versions in the family share the same parent, so a single write is
        visible to every version — no propagation or edit/publish cycle needed.
        The apprn metadata identifier is NOT added here; it is only added by
        CommitteeApprovalComponent when the public approved record is created
        (detected by the presence of source_internal_version on the public parent).
        """
        config = self._community_config()
        pattern = config["report_number_pattern"]
        report_number = self._generate_report_number(pattern)

        topic = self.request.topic.resolve()
        submitted_version_recid = (
            self.request["payload"].get("submitted_version_id") or topic["id"]
        )

        # TODO: do we not need to mint/reserve the report number when the request is created
        # rather than accepted? E.g. maybe the curators need the number before publication
        self._mint_apprn_pid(report_number, str(topic.id))

        # Write ep_approval into permission_flags — single source of truth.
        pf = topic.parent.get("permission_flags") or {}
        pf["ep_approval"] = {
            "reportnumber": report_number,
            "datetime": datetime.now(timezone.utc).isoformat(),
            "approved_internal_version": submitted_version_recid,
        }
        # TODO: why is this in `permission_flags`? It is instance-specific metadata so makes sense to go in a dict field,
        # but why not create a generic `metadata` field or something.
        topic.parent["permission_flags"] = pf
        topic.parent.commit()
        db.session.commit()

        # Store on the request payload so the UI can display it.
        self.request["payload"]["approved_report_number"] = report_number

        uow.register(
            NotificationOp(
                EPApprovalAcceptNotificationBuilder.build(
                    identity=identity,
                    request=self.request,
                )
            )
        )
        super().execute(identity, uow)


class EPApprovalDeclineAction(actions.DeclineAction):
    """Decline action — notify the submitter."""

    def execute(self, identity: Identity, uow: UnitOfWork) -> None:
        """Execute decline."""
        uow.register(
            NotificationOp(
                EPApprovalDeclineNotificationBuilder.build(
                    identity=identity,
                    request=self.request,
                )
            )
        )
        super().execute(identity, uow)


class EPApprovalRequest(RDMBaseRequest):
    """EP Approval request type.

    Allows community managers of enrolled communities to request EP committee
    approval for a specific record version. On acceptance CDS auto-generates
    a report number (e.g. CERN-EP-2026-001) and assigns it to the record.
    """

    type_id: Final[str] = "ep-approval"
    name: Final[str] = _("EP Approval")

    available_actions: Final[dict] = {
        **RDMBaseRequest.available_actions,
        "create": EPApprovalSubmitAction,
        "accept": EPApprovalAcceptAction,
        "decline": EPApprovalDeclineAction,
        "cancel": actions.CancelAction,
    }

    available_statuses: Final[dict] = {
        **RDMBaseRequest.available_statuses,
    }

    creator_can_be_none: Final[bool] = False
    topic_can_be_none: Final[bool] = False
    receiver_can_be_none: Final[bool] = False

    allowed_creator_ref_types: Final[list] = ["user"]
    allowed_receiver_ref_types: Final[list] = ["group"]
    allowed_topic_ref_types: Final[list] = ["record"]

    # Payload fields collected from the submission form.
    payload_schema: Final[dict] = {
        # Populated automatically on submit, not from the form.
        "submitted_version_id": fields.Str(load_default=None),
        # Populated on accept by the system.
        "approved_report_number": fields.Str(load_default=None),
        # Form fields.
        "experiment": fields.Str(required=True),
        "submitted_by": fields.Str(required=True),
        "role": fields.Str(required=True),
        "publication_title": fields.Str(required=True),
        "latest_version_url": fields.Str(load_default=None),
        "rapid_approval": fields.Bool(load_default=False),
        "cb_review_completed": fields.Bool(load_default=False),
        "cb_process_type": fields.Str(load_default=None),  # "standard" | "accelerated"
        "paper_signed": fields.Bool(load_default=True),
        "num_non_signers": fields.Int(load_default=0),
        "controversy": fields.Bool(load_default=False),
        "additional_communication": fields.Str(load_default=None),
    }
