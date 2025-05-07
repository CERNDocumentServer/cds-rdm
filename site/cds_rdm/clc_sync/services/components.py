# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.


"""Service components."""
from invenio_access.permissions import system_identity
from invenio_drafts_resources.services.records.components import ServiceComponent
from invenio_records_resources.services.uow import TaskOp

from cds_rdm.clc_sync.models import SyncStatusEnum
from cds_rdm.clc_sync.proxies import current_clc_sync_service
from cds_rdm.clc_sync.services.errors import CLCSyncNotExistsError

from .tasks import sync_to_clc


class ClcSyncComponent(ServiceComponent):
    """CLCSync component."""

    def publish(self, identity, draft, record, **kwargs):
        """Syncs record to CLC."""
        try:
            clc_sync_entry = current_clc_sync_service.read(
                system_identity, record["id"]
            ).to_dict()
            clc_sync_entry["status"] = SyncStatusEnum.PENDING
            clc_sync_entry["record"] = record
            current_clc_sync_service.update(
                system_identity, clc_sync_entry["id"], clc_sync_entry
            )
            self.uow.register(TaskOp(sync_to_clc, record["id"]))
        except CLCSyncNotExistsError:
            # Skip if the sync entry does not exist
            return
