# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2026 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Committee Approval notification builders."""

from __future__ import annotations

from typing import ClassVar

from flask_principal import Identity
from invenio_notifications.models import Notification
from invenio_notifications.registry import EntityResolverRegistry
from invenio_notifications.services.builders import NotificationBuilder
from invenio_notifications.services.filters import RecipientFilter
from invenio_notifications.services.generators import (
    ContextGenerator,
    EntityResolve,
    RecipientGenerator,
    UserEmailBackend,
)
from invenio_requests.records.api import Request
from invenio_users_resources.notifications.filters import UserPreferencesRecipientFilter
from invenio_users_resources.notifications.generators import UserRecipient

from .generators import GroupMembersRecipientGenerator


class CommitteeApprovalNotificationBuilder(NotificationBuilder):
    """Base notification builder for committee approval request actions."""

    type: ClassVar[str] = "committee-approval-request"

    context: ClassVar[list[ContextGenerator]] = [
        EntityResolve(key="request"),
        EntityResolve(key="request.topic"),
        EntityResolve(key="request.receiver"),
        # request.created_by and executing_user are intentionally omitted:
        # when the action is performed by system_identity there is no resolvable
        # user record, which causes a PermissionDeniedError in the users service.
    ]

    recipients: ClassVar[list[RecipientGenerator]] = []

    recipient_filters: ClassVar[list[RecipientFilter]] = [
        UserPreferencesRecipientFilter(),
    ]

    recipient_backends: ClassVar[list[UserEmailBackend]] = [
        UserEmailBackend(),
    ]

    @classmethod
    def build(cls, identity: Identity, request: Request) -> Notification:
        """Build notification."""
        return Notification(
            type=cls.type,
            context={
                "executing_user": EntityResolverRegistry.reference_identity(identity),
                "request": EntityResolverRegistry.reference_entity(request),
            },
        )


class CommitteeApprovalSubmitNotificationBuilder(CommitteeApprovalNotificationBuilder):
    """Notify the committee referee group when a request is submitted."""

    type: ClassVar[str] = f"{CommitteeApprovalNotificationBuilder.type}.submit"
    # created_by omitted: submit can be triggered by system_identity which has
    # no resolvable user record.
    recipients: ClassVar[list[RecipientGenerator]] = [
        GroupMembersRecipientGenerator("request.receiver"),
    ]


class CommitteeApprovalAcceptNotificationBuilder(CommitteeApprovalNotificationBuilder):
    """Notify the submitter when their request is accepted."""

    type: ClassVar[str] = f"{CommitteeApprovalNotificationBuilder.type}.accept"
    context: ClassVar[list[ContextGenerator]] = [
        *CommitteeApprovalNotificationBuilder.context,
        EntityResolve(key="request.created_by"),
    ]
    recipients: ClassVar[list[RecipientGenerator]] = [
        UserRecipient("request.created_by"),
    ]


class CommitteeApprovalDeclineNotificationBuilder(CommitteeApprovalNotificationBuilder):
    """Notify the submitter when their request is declined."""

    type: ClassVar[str] = f"{CommitteeApprovalNotificationBuilder.type}.decline"
    context: ClassVar[list[ContextGenerator]] = [
        *CommitteeApprovalNotificationBuilder.context,
        EntityResolve(key="request.created_by"),
    ]
    recipients: ClassVar[list[RecipientGenerator]] = [
        UserRecipient("request.created_by"),
    ]
