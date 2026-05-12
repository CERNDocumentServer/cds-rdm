# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2025 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Notification recipient generators."""

from __future__ import annotations

from typing import Any

from invenio_access.permissions import system_identity
from invenio_accounts.models import Role
from invenio_notifications.models import Notification, Recipient
from invenio_notifications.services.generators import RecipientGenerator
from invenio_records.dictutils import dict_lookup
from invenio_search.engine import dsl
from invenio_users_resources.proxies import current_users_service


class GroupMembersRecipient(RecipientGenerator):
    """Recipient generator that resolves all members of a group/role.

    Looks up the group reference at ``key`` in the notification context,
    then fetches every user belonging to that role and adds them as
    recipients.
    """

    def __init__(self, key: str) -> None:
        """Initialise with the context key pointing to the group."""
        self.key = key

    def __call__(
        self,
        notification: Notification,
        recipients: dict[str, Recipient],
    ) -> dict[str, Recipient]:
        """Add all members of the referenced group to ``recipients``."""
        group: dict[str, Any] = dict_lookup(notification.context, self.key)

        role: Role = Role.query.filter(Role.id == group["id"]).one()

        user_ids: list[str] = [str(u.id) for u in role.users]
        if not user_ids:
            return recipients

        filter_: dsl.Q = dsl.Q("terms", **{"id": user_ids})
        users = current_users_service.scan(system_identity, extra_filter=filter_)
        for u in users:
            recipients[u["id"]] = Recipient(data=u)

        return recipients
