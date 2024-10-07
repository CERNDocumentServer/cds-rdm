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


class SyncUsers(JobType):
    """Sync users with CERN database."""

    id = "sync_cern_users"
    title = "Sync CERN users"
    description = "Sync CERN users with the AuthZ service"

    task = sync_users

    @classmethod
    def build_task_arguments(cls, _, since=None, **kwargs):
        """Build task arguments."""
        return {"since": since}


class SyncGroups(JobType):
    """Sync groups with CERN database."""

    id = "sync_cern_groups"
    title = "Sync CERN groups"
    description = "Sync CERN groups with the AuthZ service"

    task = sync_groups

    @classmethod
    def build_task_arguments(cls, _, since=None, **kwargs):
        """Build task arguments."""
        return {"since": since}
