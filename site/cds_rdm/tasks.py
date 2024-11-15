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
from invenio_access.permissions import system_identity
from invenio_accounts.models import User
from invenio_cern_sync.groups.sync import sync as groups_sync
from invenio_cern_sync.users.sync import sync as users_sync
from invenio_db import db
from invenio_records_resources.proxies import current_service_registry
from invenio_records_resources.services.uow import UnitOfWork
from invenio_search.engine import dsl
from invenio_users_resources.services.users.tasks import reindex_users
from sqlalchemy.orm.exc import NoResultFound

from .utils import NamesUtils

prop_values = ["group", "department", "section"]


@shared_task
def sync_users(since=None, **kwargs):
    """Task to sync users with CERN database."""
    user_ids = users_sync(identities=dict(since=since))
    reindex_users.delay(user_ids)


@shared_task
def sync_groups(since=None, **kwargs):
    """Task to sync groups with CERN database."""
    groups_sync(groups=dict(since=since))


@shared_task()
def sync_local_accounts_to_names(since=None, user_id=None):
    """
    Syncs local accounts to the names vocabulary based on user profile data.

    This function updates or creates name entries in the vocabulary, syncing information
    such as given name, family name, email, affiliations, ORCID identifiers, and additional
    properties (e.g., group, department, section).

    The task will sync the user info in the ORCID name, when available. Otherwise, it will
    create or update the CERN name with the user info. When a CERN user adds the ORCID to the
    profile, the CERN name will be unlisted in favor of the ORCID.

    For ORCID names, the user given name and family name are not synced,
    as they are taken directly from the recurrent ORCID harvest.

    param since: The date (iso format) from which to sync the users.
    param user_id: The user id to sync.
    """
    users = []
    names_utils = NamesUtils(
        service=current_service_registry.get("names"), prop_values=prop_values
    )
    current_app.logger.info("Names sync | Starting names sync task.")
    # Allows to sync a single user
    if user_id:
        current_app.logger.debug(
            f"Names sync | Fetching active user with id {user_id}."
        )
        try:
            users = [
                User.query.filter(
                    User.id == user_id,
                    User.active == True,
                ).one()
            ]
        except Exception as e:
            current_app.logger.error(
                f"Names sync | User with id {user_id} not found or not active."
            )
            raise e
    else:
        current_app.logger.debug(
            f"Names sync | Fetching active users updated since {since}."
        )
        users = User.query.filter(
            User.updated > since,
            User.active == True,
        ).all()

    # Only keep users with a person_id
    current_app.logger.info(f"Names sync | Found {len(users)} users to sync.")
    current_app.logger.debug(f"Names sync | Filtering users with a person_id.")
    users = [user for user in users if user.user_profile.get("person_id")]
    for idx, user in enumerate(users):
        current_app.logger.info(
            f"Names sync | Syncing user {user.id}. {idx + 1}/{len(users)}"
        )
        person_id = user.user_profile["person_id"]
        try:
            current_app.logger.debug(
                f"Names sync | Fetching CERN name for user {user.id}."
            )
            cern_name = names_utils.fetch_name_by_id(person_id)
        except NoResultFound:
            current_app.logger.debug(
                f"Names sync | No CERN name found for user {user.id}."
            )
            cern_name = None
        orcid = user.user_profile.get("orcid")
        try:
            # 1. Prefer ORCID: if the user has an ORCID, we update the ORCID name with the
            # CERN user info, and we unlist any previous CERN-only name
            current_app.logger.debug(
                f"Names sync | Fetching ORCID name for user {user.id}."
            )
            orcid_name = names_utils.fetch_name_by_id(orcid)
            with UnitOfWork(db.session) as uow:
                # Unlist any previous CERN-only name
                if cern_name:
                    current_app.logger.debug(
                        f"Names sync | Unlisting CERN name for user {user.id}."
                    )
                    names_utils.update_name(user, cern_name, unlist=True, uow=uow)

                current_app.logger.debug(
                    f"Names sync | Updating ORCID name for user {user.id}."
                )
                # Update the ORCID name with the CERN user info
                names_utils.update_name(
                    user,
                    orcid_name,
                    uow=uow,
                )
                uow.commit()
        except NoResultFound:
            current_app.logger.debug(
                f"Names sync | No ORCID name found for user {user.id}."
            )
            # The CERN user does not have an ORCID, fallback to CERN name
            if cern_name:
                # 2. Existing CERN name found: we update it with the user info
                current_app.logger.debug(
                    f"Names sync | Updating CERN name for user {user.id}."
                )
                names_utils.update_name(user, cern_name)
            else:
                # 3. No CERN name found, we create a new one
                try:
                    current_app.logger.debug(
                        f"Names sync | Creating new name for user {user.id}."
                    )
                    names_utils.create_new_name(
                        user,
                    )  # Creates the name record
                except Exception as e:
                    current_app.logger.error(
                        f"Names sync | Error creating name for user {user.id}: {e}"
                    )


@shared_task()
def merge_duplicate_names_vocabulary(since=None):
    """
    Merges duplicate names in the names vocabulary based on ORCID identifiers.

    This task is meant to cover a the following corner case:
    - A user has a created the ORCID value and added it to his CERN profile.
    - The user will be synced to the names vocabulary, creating/updating the CERN name with the ORCID identifier.
    - The ORCID harvested will at some point harvest the new users data, creating a new ORCID name for that user.
    - Since the user was already synced to the names vocabulary, there will be two entries for the same user.
    - This task will merge the two entries into the ORCID value, unlisting the CERN value.

    This task identifies and merges duplicate entries in the names vocabulary when users
    have overlapping records between the CERN database and ORCID. The merging process consolidates
    all relevant data (such as affiliations, identifiers, tags, and properties) into a single
    ORCID-based record. The source records are marked as "unlisted" to indicate deprecation,
    preventing them from being displayed in search results while preserving historical integrity.

    Existing records authored by these users are not affected by the deprecation status,
    but search displays will exclude deprecated records.
    """

    def _name_is_orcid_value(name, orcid_value):
        """Check if the name is an ORCID value."""
        return name["id"] == orcid_value

    def _get_orcid_value(name):
        """Get the ORCID value from the name."""
        return next(
            (
                identifier.get("identifier")
                for identifier in name.get("identifiers", [])
                if identifier.get("scheme") == "orcid"
            ),
            None,
        )

    names_service = current_service_registry.get("names")
    names_utils = NamesUtils(service=names_service, prop_values=prop_values)
    current_app.logger.info("Names merge | Starting names merge task.")
    filters = [
        dsl.Q("term", **{"props.is_cern": True}),
        dsl.Q("term", **{"identifiers.scheme": "orcid"}),
        dsl.Q("bool", must_not=[dsl.Q("term", tags="unlisted")]),
    ]
    if since:
        filters.append(dsl.Q("range", updated={"gte": since}))
    combined_filter = dsl.Q("bool", filter=filters)
    current_app.logger.debug(
        f"Names merge | Fetching names to merge with filter: {combined_filter}"
    )
    names = names_service.scan(system_identity, extra_filter=combined_filter)
    current_app.logger.info(f"Names merge | Found {names.total} names to merge.")
    names_list = list(names.hits)
    for idx, name in enumerate(names_list):
        current_app.logger.info(
            f"Names merge | Checking name {name['id']}. {idx + 1}/{len(names_list)}"
        )
        current_app.logger.debug(
            f"Names merge | Getting orcid value for name {name['id']}."
        )
        orcid_value = _get_orcid_value(name)
        if orcid_value:
            current_app.logger.debug(
                f"Names merge | Resolving all names with orcid value {orcid_value}."
            )
            names_to_merge = names_service.resolve(
                system_identity, id_=orcid_value, id_type="orcid", many=True
            )
            if names_to_merge.total > 1:
                # We get the ORCID value and merge all the other values into it
                # (Ideally there should be only 1 value apart from the ORCID)
                orcid_name = None
                other_names = []
                for name_dest_merge in names_to_merge.hits:
                    if _name_is_orcid_value(name_dest_merge, orcid_value):
                        orcid_name = name_dest_merge
                    else:
                        other_names.append(name_dest_merge)

                if orcid_name:
                    for name_dest_merge in other_names:
                        current_app.logger.debug(
                            f"Names merge | Merging name {name_dest_merge['id']} into {orcid_name['id']}."
                        )
                        names_utils.merge(name_dest_merge, orcid_name)
