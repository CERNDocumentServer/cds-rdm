# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""CDS-RDM ldap API."""

import json
import time
import uuid
from functools import partial

from cds_rdm.ldap.client import LdapClient
from cds_rdm.ldap.user_importer import LdapUserImporter
from cds_rdm.ldap.utils import InvenioUser, serialize_ldap_user, user_exists
from flask import current_app
from invenio_db import db
from invenio_oauthclient.models import RemoteAccount
from invenio_users_resources.services.users.tasks import reindex_users


def get_ldap_users(log_func):
    """Create and return a map of all LDAP users."""
    ldap_users_emails = set()
    ldap_users_map = {}

    # get all CERN users from LDAP
    ldap_client = LdapClient()
    ldap_users = ldap_client.get_primary_accounts()
    ldap_users_count = len(ldap_users)

    log_func("ldap_users_fetched", dict(users_fetched=ldap_users_count))

    for ldap_user_data in ldap_users:
        ldap_user = serialize_ldap_user(ldap_user_data, log_func=log_func)

        if ldap_user and ldap_user["user_email"] not in ldap_users_emails:
            ldap_person_id = ldap_user["remote_account_person_id"]
            ldap_users_map[ldap_person_id] = ldap_user
            ldap_users_emails.add(ldap_user["user_email"])

    log_func("ldap_users_cached")
    return ldap_users_count, ldap_users_map, ldap_users_emails


def remap_invenio_users(log_func):
    """Create and return a list of all Invenio users."""
    invenio_remote_accounts_list = []
    remote_accounts = RemoteAccount.query.all()

    log_func("invenio_users_fetched", dict(users_fetched=len(remote_accounts)))

    # get all Invenio remote accounts and prepare a list with needed info
    for remote_account in remote_accounts:
        invenio_remote_accounts_list.append(remote_account)
    log_func("invenio_users_cached")
    return invenio_remote_accounts_list


def _log_info(log_uuid, action, extra=dict(), is_error=False):
    name = "ldap_users_synchronization"
    structured_msg = dict(name=name, uuid=log_uuid, action=action, **extra)
    structured_msg_str = json.dumps(structured_msg, sort_keys=True)
    if is_error:
        current_app.logger.error(structured_msg_str)
    else:
        current_app.logger.info(structured_msg_str)


def update_users():
    """Sync LDAP users with local users in the DB."""

    def update_invenio_users_from_ldap(remote_accounts, ldap_users_map, log_func):
        """Iterate on all Invenio users to update outdated info from LDAP."""
        updated_count = 0
        user_ids = []
        # Note: cannot iterate on the db query here, because when a user is
        # deleted, db session will expire, causing a DetachedInstanceError when
        # fetching the user on the next iteration
        for remote_account in remote_accounts:
            invenio_user = InvenioUser(remote_account)
            # use `dict.pop` to remove from `ldap_users_map` the users found
            # in Invenio, so the remaining will be the ones to be added
            # later on
            ldap_user = ldap_users_map.pop(
                invenio_user.data["remote_account_person_id"], None
            )
            if not ldap_user:
                continue

            invenio_user.data.pop("remote_account_id")
            ldap_user.pop("cern_account_type")

            has_changed = invenio_user.data != ldap_user

            if has_changed:
                invenio_user.update(ldap_user)
                user_ids.append(invenio_user.user_id)
                db.session.commit()
                log_func(
                    "user_updated",
                    dict(
                        user_id=invenio_user.user_id,
                        previous_department=invenio_user.data[
                            "remote_account_department"
                        ],
                        new_department=ldap_user["remote_account_department"],
                    ),
                )

                updated_count += 1

        db.session.commit()
        reindex_users.delay(user_ids)
        log_func("invenio_users_updated_from_ldap", dict(count=updated_count))

        return ldap_users_map, updated_count

    def import_new_ldap_users(new_ldap_users, log_func):
        """Import any new LDAP user not in Invenio yet."""
        importer = LdapUserImporter()
        added_count = 0
        user_ids = []
        for ldap_user in new_ldap_users:
            # Check if email already exists in Invenio.
            # Apparently, in some cases, there could be multiple LDAP users
            # with different person id but same email.
            if not ldap_user:
                continue
            if user_exists(ldap_user):
                log_func(
                    "ldap_user_skipped_user_exists",
                    dict(
                        email=ldap_user["user_email"],
                        person_id=ldap_user["remote_account_person_id"],
                    ),
                )
                continue
            email = ldap_user["user_email"]
            employee_id = ldap_user["remote_account_person_id"]

            user_id = importer.import_user(ldap_user)
            user_ids.append(user_id)
            log_func(
                "invenio_user_added",
                dict(email=email, employee_id=employee_id),
            )

            added_count += 1

        db.session.commit()
        reindex_users.delay(user_ids)
        log_func("import_new_users_done", dict(count=added_count))

        return added_count

    log_uuid = str(uuid.uuid4())
    log_func = partial(_log_info, log_uuid)
    start_time = time.time()

    ldap_users_count, ldap_users_map, ldap_users_emails = get_ldap_users(log_func)

    if not ldap_users_emails:
        return 0, 0, 0

    remote_accounts = remap_invenio_users(log_func)

    # STEP 1 - update Invenio users with info from LDAP
    ldap_users_map, invenio_users_updated = update_invenio_users_from_ldap(
        remote_accounts, ldap_users_map, log_func
    )

    # STEP 2 - import any new LDAP user not in Invenio yet
    invenio_users_added = 0
    new_ldap_users = ldap_users_map.values()

    if new_ldap_users:
        invenio_users_added = import_new_ldap_users(new_ldap_users, log_func)

    total_time = time.time() - start_time

    log_func("task_completed", dict(time=total_time))

    return (
        ldap_users_count,
        invenio_users_updated,
        invenio_users_added,
    )
