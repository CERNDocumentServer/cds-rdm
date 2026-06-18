# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2026 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Helpers for creating a public record following an accepted EP Approval request."""

"""Create a public approved record from an approved draft.

Requires the calling user to be a community manager/owner of the
record's enrolled community.

Steps:
1. Read the approved draft — must have ep_approval.reportnumber set on parent.
2. Build a new public record: copy metadata + files, set access=public.
3. Create draft, import files, write ep_approval to both parents, publish.
4. Return the new public record id and links.
"""


from invenio_pidstore.models import PersistentIdentifier
from invenio_rdm_records.records.api import RDMRecord


def get_record_ep_approval(pid_value: str):
    """Return the EP Approval object for a record by PID."""
    src_pid_obj = PersistentIdentifier.get("recid", pid_value)
    src_rec_obj = RDMRecord.get_record(src_pid_obj.object_uuid)
    ea = (src_rec_obj.parent.get("permission_flags") or {}).get("ep_approval") or {}
    return ea
