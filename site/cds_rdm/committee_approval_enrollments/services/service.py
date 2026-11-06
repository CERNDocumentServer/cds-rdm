# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Committee approval communities service."""

from invenio_db.uow import unit_of_work
from invenio_records_resources.services import RecordService
from sqlalchemy.exc import IntegrityError

from .errors import (
    CommitteeApprovalEnrollmentAlreadyExistsError,
    CommitteeApprovalEnrollmentNotFoundError,
)


class CommitteeApprovalEnrollmentService(RecordService):
    """CRUD service for committee approval communities."""

    def _get(self, id):
        obj = self.record_cls.get_by_id(id)
        if obj is None:
            raise CommitteeApprovalEnrollmentNotFoundError(id)
        return obj

    def _item(self, identity, obj):
        return self.result_item(self, identity, obj, links_tpl=self.links_item_tpl)

    def read(self, identity, id, **kwargs):
        """Read an entry."""
        self.require_permission(identity, "read")
        return self._item(identity, self._get(id))

    def search(self, identity, params=None, **kwargs):
        """Search entries."""
        self.require_permission(identity, "search")
        results = self.record_cls.search(params or {})
        return self.result_list(
            self, identity, results, links_item_tpl=self.links_item_tpl
        )

    @unit_of_work()
    def create(self, identity, data, uow=None, **kwargs):
        """Create an entry."""
        self.require_permission(identity, "create")
        valid, _ = self.schema.load(
            data, context={"identity": identity}, raise_errors=True
        )
        if self.record_cls.get_by_community_id(valid["community_id"]):
            raise CommitteeApprovalEnrollmentAlreadyExistsError(valid["community_id"])
        try:
            obj = self.record_cls.create(valid)
        except IntegrityError as e:
            raise CommitteeApprovalEnrollmentAlreadyExistsError(
                valid["community_id"]
            ) from e
        return self._item(identity, obj)

    @unit_of_work()
    def update(self, identity, id, data, uow=None, **kwargs):
        """Update an entry."""
        self.require_permission(identity, "update")
        obj = self._get(id)
        # the enrolled community cannot be changed once created
        data = {**data, "community_id": str(obj.community_id)}
        valid, _ = self.schema.load(
            data, context={"identity": identity}, raise_errors=True
        )
        valid.pop("community_id")
        self.record_cls.update(obj, valid)
        return self._item(identity, obj)

    @unit_of_work()
    def delete(self, identity, id, uow=None, **kwargs):
        """Delete an entry."""
        self.require_permission(identity, "delete")
        obj = self._get(id)
        self.record_cls.delete(obj)
        return self._item(identity, obj)
