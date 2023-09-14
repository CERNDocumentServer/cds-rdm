# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""CDS-RDM invenio user importer API."""

from flask import current_app
from flask_security.confirmable import confirm_user
from invenio_accounts.models import User
from invenio_db import db
from invenio_oauthclient.models import RemoteAccount, UserIdentity
from invenio_userprofiles.models import UserProfile


class LdapUserImporter:
    """Import ldap users to Invenio RDM records.

    Expected input format for ldap users:
        [
            {'displayName': [b'Joe Foe'],
             'department': [b'IT/CDA'],
             'uidNumber': [b'100000'],
             'mail': [b'joe.foe@cern.ch'],
             'cernAccountType': [b'Primary'],
             'employeeID': [b'101010']
            },...
        ]
    """

    def __init__(self, remote_account_client_id):
        """Constructor."""
        self.client_id = remote_account_client_id

    def create_invenio_user(self, ldap_user):
        """Commit new user in db."""
        email = ldap_user["user_email"]
        username = ldap_user["user_username"]
        user = User(email=email, username=username, active=True)
        db.session.add(user)
        db.session.commit()
        return user

    def create_invenio_user_identity(self, user_id, ldap_user):
        """Return new user identity entry."""
        uid_number = ldap_user["user_identity_id"]
        return UserIdentity(
            id=uid_number,
            method=current_app.config["OAUTH_REMOTE_APP_NAME"],
            id_user=user_id,
        )

    def create_invenio_user_profile(self, user, ldap_user):
        """Return new user profile."""
        user_profile = UserProfile(user=user)
        user_profile.full_name = ldap_user["user_profile_full_name"]
        return user_profile

    def create_invenio_remote_account(self, user_id, ldap_user):
        """Return new user entry."""
        keycloak_id = ldap_user["user_username"]
        employee_id = ldap_user["remote_account_person_id"]
        department = ldap_user["remote_account_department"]
        return RemoteAccount.create(
            client_id=self.client_id,
            user_id=user_id,
            extra_data=dict(
                keycloak_id=keycloak_id, person_id=employee_id, department=department
            ),
        )

    def import_user(self, ldap_user):
        """Create Invenio users from LDAP export."""
        user = self.create_invenio_user(ldap_user)
        user_id = user.id

        identity = self.create_invenio_user_identity(user_id, ldap_user)
        db.session.add(identity)

        profile = self.create_invenio_user_profile(user, ldap_user)
        db.session.add(profile)

        remote_account = self.create_invenio_remote_account(user_id, ldap_user)
        db.session.add(remote_account)

        # Automatically confirm the user
        confirm_user(user)
        return user_id
