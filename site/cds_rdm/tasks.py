# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2023 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Celery tasks for cds."""

from celery import shared_task
from invenio_cern_sync.groups.sync import sync as groups_sync
from invenio_cern_sync.users.sync import sync as users_sync
from invenio_users_resources.services.users.tasks import reindex_users


@shared_task
def sync_users(since=None, **kwargs):
    """Task to sync users with CERN database."""
    user_ids = users_sync(identities=dict(since=since))
    reindex_users.delay(user_ids)


@shared_task
def sync_groups(since=None, **kwargs):
    """Task to sync groups with CERN database."""
    groups_sync(groups=dict(since=since))
