# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2025 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Notification recipient generators."""

from __future__ import annotations

from flask import current_app
from invenio_communities.notifications.generators import CommunityMembersRecipient
from invenio_notifications.models import Notification, Recipient
from invenio_notifications.services.generators import RecipientGenerator
from invenio_pidstore.models import PersistentIdentifier
from invenio_rdm_records.records.api import RDMRecord
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


class EPWorkflowCommunityMembersRecipient(RecipientGenerator):
    """Recipient generator for the managers and owners of the record's EP community.

    Looks up the (resolved) record at ``key`` in the notification context and, if
    its default community is enrolled in the committee approval workflow, adds the
    members of that community with one of ``roles`` as recipients.
    """

    def __init__(self, key: str, roles: tuple = ("manager", "owner")) -> None:
        """Initialise with the context key pointing to the record."""
        self.key = key
        self.roles = list(roles)

    def _default_community_id(self, record):
        """Return the default community id of the record, if any."""
        parent = getattr(record, "parent", None)
        if parent is None:
            pid = PersistentIdentifier.get("recid", record["id"])
            parent = RDMRecord.get_record(pid.object_uuid).parent
        return (parent.get("communities") or {}).get("default")

    def __call__(
        self,
        notification: Notification,
        recipients: dict[str, Recipient],
    ) -> dict[str, Recipient]:
        """Add the community managers and owners to ``recipients``."""
        record = dict_lookup(notification.context, self.key)
        community_id = self._default_community_id(record)
        enrolled = current_app.config.get("CDS_COMMITTEE_APPROVAL_COMMUNITIES", {})
        if not community_id or community_id not in enrolled:
            return recipients

        notification.context["_ep_community"] = {"id": community_id}
        try:
            return CommunityMembersRecipient("_ep_community", roles=self.roles)(
                notification, recipients
            )
        finally:
            notification.context.pop("_ep_community", None)
