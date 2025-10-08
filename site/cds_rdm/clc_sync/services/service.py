# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""CLCSync service."""

import distutils.util

import arrow
import requests
from flask import current_app
from invenio_db.uow import unit_of_work
from invenio_records_resources.services import RecordService
from sqlalchemy.exc import IntegrityError

from ..models import SyncStatusEnum
from .errors import CLCSyncAlreadyExistsError
from .utils import clc_import


class CLCSyncService(RecordService):
    """CLC Sync  Service."""

    def read(self, identity, id):
        """Retrieve a sync entry."""
        self.require_permission(identity, "read")
        try:
            sync_obj = self.record_cls.get_by_id(id)
        except Exception:
            sync_obj = self.record_cls.get_by_parent_record_pid(id)

        return self.result_item(
            self,
            identity,
            sync_obj,
            links_tpl=self.links_item_tpl,
        )

    def _clc_import(self, data):
        """Call the CLC import API."""
        record_data = data.get("record")
        auto_sync = data.get("auto_sync", True)  # Default to True

        if not record_data or not auto_sync:
            return  # Skip
        resource = record_data["metadata"]["resource_type"]["id"]
        if not any(
            resource.startswith(allowed)
            for allowed in current_app.config["CLC_SYNC_ALLOWED_RESOURCE_TYPES"]
        ):
            data["message"] = f"Resource type {resource} not allowed to sync."
            data["status"] = SyncStatusEnum.FAILED
            return

        try:
            response_data = clc_import(record_data)
            data["last_sync"] = arrow.utcnow().isoformat()
            data["clc_record_pid"] = response_data["metadata"]["pid"]
            data["status"] = SyncStatusEnum.SUCCESS
            data["message"] = "CLC Import call succeeded"
        except requests.RequestException as e:
            error_message = f"CLC Import call failed: {str(e)}"
            data["message"] = error_message
            data["status"] = SyncStatusEnum.FAILED

    @unit_of_work()
    def create(self, identity, data, raise_errors=True, uow=None):
        """Create a sync entry."""
        self.require_permission(identity, "create")
        self._clc_import(data)

        # validate data
        valid_data, errors = self.schema.load(
            data,
            context={"identity": identity},
            raise_errors=raise_errors,
        )
        try:
            if "status" not in valid_data:
                valid_data["status"] = SyncStatusEnum.SUCCESS
            sync = self.record_cls.create(valid_data)
        except IntegrityError as e:
            error_msg = str(e.orig)
            if "idx_parent_record_pid" in error_msg or "parent_record_pid" in error_msg:
                raise CLCSyncAlreadyExistsError(
                    f"A sync entry already exists for the CDS record '{valid_data['parent_record_pid']}'."
                ) from e
            elif "idx_cls_record_pid" in error_msg or "clc_record_pid" in error_msg:
                raise CLCSyncAlreadyExistsError(
                    f"A sync entry already exists for the CLC record '{valid_data['clc_record_pid']}'."
                ) from e
            else:
                raise

        return self.result_item(
            self, identity, sync, links_tpl=self.links_item_tpl, errors=errors
        )

    @unit_of_work()
    def delete(self, identity, id, uow=None):
        """Delete a sync entry from database."""
        self.require_permission(identity, "delete")

        sync = self.record_cls.get_by_id(id)
        self.record_cls.delete(sync)

        return self.result_item(self, identity, sync, links_tpl=self.links_item_tpl)

    @unit_of_work()
    def update(self, identity, id, data, uow=None):
        """Update a sync entry."""
        self.require_permission(identity, "update")
        self._clc_import(data)

        # validate data
        valid_data, errors = self.schema.load(
            data,
            context={"identity": identity},
            raise_errors=True,
        )

        updated_sync = self.record_cls.update(valid_data, id)

        return self.result_item(
            self,
            identity,
            updated_sync,
            links_tpl=self.links_item_tpl,
        )

    def search(
        self, identity, params=None, search_preference=None, expand=False, **kwargs
    ):
        """Search for records matching the querystring."""
        self.require_permission(identity, "search")
        users_sync = self.record_cls.search(params)
        return self.result_list(
            self,
            identity,
            users_sync,
            links_tpl=self.links_item_tpl,
        )
