# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""CLCSync tasks."""

import requests
from celery import shared_task
from invenio_access.permissions import system_identity
from invenio_rdm_records.proxies import current_rdm_records_service

from cds_rdm.clc_sync.proxies import current_clc_sync_service
from cds_rdm.clc_sync.services.errors import CLCSyncError, CLCSyncNotExistsError


@shared_task
def sync_to_clc(record_id):
    """Celery task to sync a record to the CLC system."""
    try:
        clc_sync_entry = current_clc_sync_service.read(
            system_identity, record_id
        ).to_dict()
        if not clc_sync_entry.get("auto_sync"):
            # Skip if auto_sync is set to false
            return
        record_result = current_rdm_records_service.read(system_identity, record_id)
        clc_sync_entry["record"] = record_result.to_dict()
        clc_sync = current_clc_sync_service.update(
            system_identity, clc_sync_entry["id"], clc_sync_entry
        )
        clc_dict = clc_sync.to_dict()
        if clc_dict.get("status") == "FAILED":
            raise CLCSyncError(
                f"Failed to sync record ({clc_dict.get('parent_record_pid')}) to CLC. Error: {clc_dict.get('message')}"
            )
    except CLCSyncNotExistsError:
        # Skip if the sync entry does not exist
        return
    except Exception as e:
        raise CLCSyncError(f"Sync record to CLC failed: {str(e)}") from e
