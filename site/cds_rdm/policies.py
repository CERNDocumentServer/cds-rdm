# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2026 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""CDS specific policies."""

from invenio_i18n import lazy_gettext as _
from invenio_rdm_records.services.request_policies import BasePolicy

from .administration.permissions import harvester_admin_access_permission


class FileModificationHarvesterPolicy(BasePolicy):
    """File modification policy which allows the INSPIRE harvester to modify files of all records."""

    id = "file-modification-harvester-v1"
    description = _("INSPIRE harvester can edit the files of the record.")

    def is_allowed(self, identity, record=None):
        """INSPIRE Harvester is allowed."""
        return harvester_admin_access_permission.allows(identity)

    def evaluate(self, identity, record):
        """Can only modify records with external DOI."""
        return (record.pids.get("doi") or {}).get("provider") == "external"
