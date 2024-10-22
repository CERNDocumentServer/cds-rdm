# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2024 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Jobs."""

from invenio_jobs.jobs import JobType

from .tasks import sync_local_accounts_to_names, merge_duplicate_names_vocabulary
from datetime import datetime, timedelta

class SyncLocalAccounts(JobType):
    """Job to sync local accounts to names."""

    id = "sync_local_accounts_to_names"
    title = "Sync local accounts to names"
    description = "Sync local accounts to names vocabulary."
    task = sync_local_accounts_to_names


    @classmethod
    def build_task_arguments(cls, job_obj, since=None, user_id=None, **kwargs):
        """Build task arguments."""
        if since is None and job_obj.last_runs["success"]:
            since = job_obj.last_runs["success"].started_at
        else:
            since = (datetime.now() - timedelta(days=1)).isoformat()

        return {"since": since, "user_id": user_id}
    
class MergeDuplicateNames(JobType):
    """Job to merge duplicate names."""

    id = "merge_duplicate_names"
    title = "Merge duplicate names"
    description = "Merge duplicate names in the names vocabulary."
    task = merge_duplicate_names_vocabulary

    @classmethod
    def build_task_arguments(cls, job_obj, since=None, **kwargs):
        """Build task arguments."""
        if since is None and job_obj.last_runs["success"]:
            since = job_obj.last_runs["success"].started_at
        else:
            since = (datetime.now() - timedelta(days=1)).isoformat()

        return {"since": since}
    

