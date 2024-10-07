# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2023 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Celery tasks for cds."""

from celery import shared_task
from flask import current_app
from invenio_cern_sync.groups.sync import sync as groups_sync
from invenio_cern_sync.users.sync import sync as users_sync
from invenio_db import db
from invenio_users_resources.services.users.tasks import reindex_users


@shared_task
def sync_users(*args, **kwargs):
    """Task to sync users with CERN database."""
    if current_app.config.get("DEBUG", True):
        current_app.logger.warning("Users sync disabled, the DEBUG env var is True.")
        return

    last_run = kwargs["last_run"]  # isoformat datetime
    try:
        user_ids = users_sync(identities=dict(since=last_run))
        reindex_users.delay(user_ids)
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(e)


@shared_task
def sync_groups(*args, **kwargs):
    """Task to sync groups with CERN database."""
    if current_app.config.get("DEBUG", True):
        current_app.logger.warning("Groups sync disabled, the DEBUG env var is True.")
        return

    last_run = kwargs["last_run"]  # isoformat datetime
    try:
        groups_sync(groups=dict(since=last_run))
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(e)
