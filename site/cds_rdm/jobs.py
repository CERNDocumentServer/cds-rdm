# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2023 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Jobs."""

from invenio_jobs.jobs import JobType

from .tasks import sync_groups, sync_users

sync_cern_users = JobType.create(
    arguments_schema=None,
    job_cls_name="SyncCERNUsersJob",
    id_="sync_cern_users",
    task=sync_users,
    description="Sync CERN users with the AuthZ service",
    title="Sync CERN users",
)

sync_cern_groups = JobType.create(
    arguments_schema=None,
    job_cls_name="SyncCERNGroupsJob",
    id_="sync_cern_groups",
    task=sync_groups,
    description="Sync CERN groups with the AuthZ service",
    title="Sync CERN groups",
)
