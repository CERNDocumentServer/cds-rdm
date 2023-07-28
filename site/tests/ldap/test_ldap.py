# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Test LDAP functions."""

from copy import deepcopy

import pytest
from flask import current_app
from invenio_access.permissions import system_identity
from invenio_accounts.models import User
from invenio_oauthclient.models import RemoteAccount
from invenio_userprofiles.models import UserProfile
from invenio_users_resources.proxies import current_users_service
from invenio_users_resources.services.users.tasks import reindex_users
from sqlalchemy.exc import IntegrityError

from cds_rdm.ldap.api import LdapUserImporter, update_users
from cds_rdm.ldap.utils import serialize_ldap_user


def test_update_users(app, db, mocker):
    """Test update users with LDAP."""
    ldap_users = [
        {
            "displayName": [b"New user"],
            "cn": [b"newuser"],
            "department": [b"A department"],
            "uidNumber": [b"111"],
            "mail": [b"ldap.user111@cern.ch"],
            "cernAccountType": [b"Primary"],
            "employeeID": [b"00111"],
            "postOfficeBox": [b"M12345"],
        },
        {
            "displayName": [b"A new name"],
            "cn": [b"anewname"],
            "department": [b"A new department"],
            "uidNumber": [b"222"],
            "mail": [b"ldap.user222@cern.ch"],
            "cernAccountType": [b"Primary"],
            "employeeID": [b"00222"],
            "postOfficeBox": [b"M12345"],
        },
        {
            "displayName": [b"Nothing changed"],
            "cn": [b"nothingchanged"],
            "department": [b"Same department"],
            "uidNumber": [b"333"],
            "mail": [b"ldap.user333@cern.ch"],
            "cernAccountType": [b"Primary"],
            "employeeID": [b"00333"],
            "postOfficeBox": [b"M12345"],
        },
        {
            "displayName": [b"Name 1"],
            "cn": [b"name1"],
            "department": [b"Department 1"],
            "uidNumber": [b"555"],
            "mail": [b"ldap.user555@cern.ch"],
            "cernAccountType": [b"Primary"],
            "employeeID": [b"00555"],
            "postOfficeBox": [b"M12345"],
        },
        {
            "displayName": [b"Name 2"],
            "cn": [b"name2"],
            "department": [b"Department 2"],
            "uidNumber": [b"666"],
            "mail": [b"ldap.user555@cern.ch"],  # same email as 555
            "cernAccountType": [b"Primary"],
            "employeeID": [b"00666"],
            "postOfficeBox": [b"M12345"],
        },
        {
            "displayName": [b"Name"],
            "cn": [b"name"],
            "department": [b"Department"],
            "uidNumber": [b"777"],
            # missing email, should be skipped
            "cernAccountType": [b"Primary"],
            "employeeID": [b"00777"],
            "postOfficeBox": [b"M12345"],
        },
        {
            "displayName": [b"Name"],
            "cn": [b"name"],
            "department": [b"Department"],
            "uidNumber": [b"999"],
            # custom emails allowed
            "mail": [b"ldap.user999@test.ch"],
            "cernAccountType": [b"Primary"],
            "employeeID": [b"00999"],
            "postOfficeBox": [b"M12345"],
        },
        {
            "displayName": [b"Nothing changed"],
            "cn": [b"nothingchanged"],
            "department": [b"Same department"],
            "uidNumber": [b"333"],
            # same email as 333, different employee ID, should be skipped
            "mail": [b"ldap.user333@cern.ch"],
            "cernAccountType": [b"Primary"],
            "employeeID": [b"9152364"],
            "postOfficeBox": [b"M12345"],
        },
        {
            "displayName": [b"Name"],
            "cn": [b"name"],
            "department": [b"Department"],
            "uidNumber": [b"444"],
            # empty email should be skipped
            "mail": [b""],
            "cernAccountType": [b"Primary"],
            "employeeID": [b"00444"],
            "postOfficeBox": [b"M12345"],
        },
    ]

    def _prepare():
        """Prepare data."""
        remote_account_client_id = current_app.config["CERN_APP_CREDENTIALS"][
            "consumer_key"
        ]
        importer = LdapUserImporter(remote_account_client_id)
        # Prepare users in DB. Use `LdapUserImporter` to make it easy
        # create old users
        WILL_BE_UPDATED = deepcopy(ldap_users[1])
        WILL_BE_UPDATED["displayName"] = [b"Previous name"]
        WILL_BE_UPDATED["cn"] = [b"previousname"]
        WILL_BE_UPDATED["department"] = [b"Old department"]
        ldap_user = serialize_ldap_user(WILL_BE_UPDATED)
        importer.import_user(ldap_user)

        WILL_NOT_CHANGE = deepcopy(ldap_users[2])
        ldap_user = serialize_ldap_user(WILL_NOT_CHANGE)
        user_id1 = importer.import_user(ldap_user)

        # create a user that does not exist anymore in LDAP, but will not
        # be deleted for safety
        COULD_BE_DELETED = {
            "displayName": [b"old user left CERN"],
            "cn": [b"olduserleftcern"],
            "department": [b"Department"],
            "uidNumber": [b"444"],
            "mail": [b"ldap.user444@cern.ch"],
            "cernAccountType": [b"Primary"],
            "employeeID": [b"00444"],
            "postOfficeBox": [b"M12345"],
        }
        ldap_user = serialize_ldap_user(COULD_BE_DELETED)
        user_id2 = importer.import_user(ldap_user)
        db.session.commit()
        reindex_users.delay([user_id1, user_id2])

    def _prepare_duplicate():
        duplicated = {
            "displayName": [b"Name 2"],
            "cn": [b"name2"],
            "department": [b"Department 2"],
            # same id as one of the previous, different emails
            # should be skipped
            "uidNumber": [b"555"],
            "mail": [b"other555@cern.ch"],
            "cernAccountType": [b"Primary"],
            "employeeID": [b"00555"],
            "postOfficeBox": [b"M12345"],
        }
        remote_account_client_id = current_app.config["CERN_APP_CREDENTIALS"][
            "consumer_key"
        ]
        importer = LdapUserImporter(remote_account_client_id)
        ldap_user = serialize_ldap_user(duplicated)
        user_id1 = importer.import_user(ldap_user)
        db.session.commit()
        reindex_users.delay(user_id1)

    _prepare()

    # mock LDAP response
    mocker.patch(
        "cds_rdm.ldap.client.LdapClient.get_primary_accounts",
        return_value=ldap_users,
    )

    n_ldap, n_updated, n_added = update_users()
    current_users_service.indexer.process_bulk_queue()
    current_users_service.record_cls.index.refresh()

    assert n_ldap == 9
    assert n_updated == 1  # 00222
    assert n_added == 3  # 00111, 00555, 00999

    invenio_users = User.query.all()
    # 4 in the prepared data
    # 2 newly added from LDAP
    assert len(invenio_users) == 6

    def check_existence(
        expected_email,
        expected_username,
        expected_name,
        expected_department,
        expected_person_id,
        expected_mailbox,
    ):
        """Assert exist in DB and ES."""
        # check if saved in DB
        user = User.query.filter_by(email=expected_email).one()
        up = UserProfile.get_by_userid(user.id)
        assert up.full_name == expected_name
        ra = RemoteAccount.query.filter_by(user_id=user.id).one()
        assert ra.extra_data["department"] == expected_department
        assert ra.extra_data["person_id"] == expected_person_id

        # check if indexed correctly
        results = current_users_service.search(
            system_identity, q=f"username:{user.username}"
        )
        assert results.total == 1
        patron_hit = [r for r in results][0]
        assert patron_hit["email"] == expected_email
        assert patron_hit["username"] == expected_username

    check_existence(
        "ldap.user111@cern.ch", "newuser", "New user", "A department", "00111", "M12345"
    )
    check_existence(
        "ldap.user222@cern.ch",
        "anewname",
        "A new name",
        "A new department",
        "00222",
        "M12345",
    )
    check_existence(
        "ldap.user333@cern.ch",
        "nothingchanged",
        "Nothing changed",
        "Same department",
        "00333",
        "M12345",
    )
    check_existence(
        "ldap.user444@cern.ch",
        "olduserleftcern",
        "old user left CERN",
        "Department",
        "00444",
        "M12345",
    )
    check_existence(
        "ldap.user555@cern.ch", "name1", "Name 1", "Department 1", "00555", "M12345"
    )

    # try ot import duplicated userUID
    with pytest.raises(IntegrityError):
        _prepare_duplicate()
