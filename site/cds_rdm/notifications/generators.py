# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2025 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Notification recipient generators."""

from __future__ import annotations

from invenio_notifications.models import Notification, Recipient
from invenio_notifications.services.generators import RecipientGenerator
from invenio_records.dictutils import dict_lookup


class GroupEmailRecipientGenerator(RecipientGenerator):
    """Recipient generator that sends to the CERN e-group mailing address.

    Looks up the group reference at ``key`` in the notification context and
    derives the group email as ``{name}@cern.ch``.  This avoids querying the
    ``role.users`` DB relationship, which is only populated when members have
    previously logged in — CERN e-group membership lives on the SSO token, not
    in the local DB.
    """

    def __init__(self, key: str) -> None:
        """Initialise with the context key pointing to the group."""
        self.key = key

    def __call__(
        self,
        notification: Notification,
        recipients: dict[str, Recipient],
    ) -> dict[str, Recipient]:
        """Add the group mailing address to ``recipients``.

        After ``EntityResolve`` runs, the context value at ``key`` is the resolved
        ``Role`` ORM object. We read ``role.name`` to derive the CERN e-group email.
        """
        group = dict_lookup(notification.context, self.key)
        name = group.get("name", "") if isinstance(group, dict) else ""
        if not name:
            return recipients
        recipients[name] = Recipient(data={"email": f"{name}@cern.ch"})
        return recipients
