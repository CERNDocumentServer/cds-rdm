# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""CDS-RDM CLC config sync module."""

from invenio_i18n import gettext as _
from invenio_records_resources.services import Link, RecordServiceConfig
from invenio_records_resources.services.records.links import pagination_links
from sqlalchemy import asc, desc

from ..models import CDSToCLCSyncModel
from .permissions import CLCSyncPermissionPolicy
from .results import SyncItem, SyncList
from .schema import CLCSyncSchema


class CLCSyncServiceConfig(RecordServiceConfig):
    """Service factory configuration."""

    result_item_cls = SyncItem
    result_list_cls = SyncList
    permission_policy_cls = CLCSyncPermissionPolicy
    schema = CLCSyncSchema
    record_cls = CDSToCLCSyncModel
