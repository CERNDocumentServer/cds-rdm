# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2023 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Celery tasks for cds."""
import requests
from celery import shared_task
from flask import current_app
from invenio_db import db
from invenio_oauthclient.handlers.base import create_or_update_groups

from cds_rdm.errors import RequestError
from cds_rdm.ldap.api import update_users


@shared_task(
    bind=True, max_retries=6, default_retry_delay=60 * 10
)  # Retry every 10 min for 1 hour
def synch_groups(self):
    """Synchronizes groups in CDS."""
    token_url = (
        f"{current_app.config['CERN_KEYCLOAK_URL']}auth/realms/cern/api-access/token"
    )
    token_data = {
        "grant_type": "client_credentials",
        "client_id": current_app.config["CERN_APP_CREDENTIALS"]["consumer_key"],
        "client_secret": current_app.config["CERN_APP_CREDENTIALS"]["consumer_secret"],
        "audience": "authorization-service-api",  # This is the target api of the token
    }
    try:
        token_response = requests.post(url=token_url, data=token_data)
    except Exception as e:
        while self.request.retries < self.max_retries:
            self.retry()
        raise RequestError(token_url, str(e))

    if not token_response.ok:
        while self.request.retries < self.max_retries:
            self.retry()
        raise RequestError(
            token_url,
            f"Request failed with status code {token_response.status_code} {token_response.reason}.",
        )

    token = token_response.json()["access_token"]
    offset = 0
    limit = 1000
    groups_headers = {
        "Authorization": f"Bearer {token}",
        "accept": "text/plain",
    }

    # We do this to get the total amount of entries, to be able to create as many celery tasks as required
    groups_url = f"{current_app.config['CDS_AUTHORIZATION_SERVICE_API']}{current_app.config['CDS_AUTHORIZATION_SERVICE_API_GROUP_URL'].format(offset=0, limit=1)}"
    try:
        groups_response = requests.get(url=groups_url, headers=groups_headers)
    except Exception as e:
        while self.request.retries < self.max_retries:
            self.retry()
        raise RequestError(groups_url, str(e))

    if not groups_response.ok:
        while self.request.retries < self.max_retries:
            self.retry()
        raise RequestError(
            groups_url,
            f"Request failed with status code {groups_response.status_code}, {groups_response.reason}.",
        )

    total = groups_response.json()["pagination"]["total"]
    while offset < total:
        update_groups.delay(offset, limit, groups_headers)
        offset += limit


@shared_task(
    bind=True, max_retries=6, default_retry_delay=10 * 60
)  # Retry every 10 min for 1 hour
def update_groups(self, offset, limit, groups_headers):
    """Celery task to fetch and update groups.

    :param offset: Offset to be sent in the request.
    :param limit: Limit to be sent in the request.
    :param groups_headers: Headers of the request.
    """
    groups_url = f"{current_app.config['CDS_AUTHORIZATION_SERVICE_API']}{current_app.config['CDS_AUTHORIZATION_SERVICE_API_GROUP_URL'].format(offset=offset, limit=limit)}"
    try:
        groups_response = requests.get(url=groups_url, headers=groups_headers)
    except Exception as e:
        while self.request.retries < self.max_retries:
            self.retry()
        raise RequestError(groups_url, e)

    if not groups_response.ok:
        while self.request.retries < self.max_retries:
            self.retry()
        raise RequestError(
            groups_url,
            f"Request failed with status code {groups_response.status_code}, {groups_response.reason}.",
        )

    serialized_groups = []
    for group in groups_response.json()["data"]:
        serialized_groups.append(
            {
                "id": group["groupIdentifier"],
                "name": group["displayName"],
                "description": group["description"],
            }
        )
    create_or_update_groups(serialized_groups)


@shared_task
def synch_users():
    """Run the task to update users from LDAP."""
    try:
        update_users()
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(e)
