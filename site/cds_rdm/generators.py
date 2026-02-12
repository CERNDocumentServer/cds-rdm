# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2023 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Permissions generators."""

from flask import current_app
from flask_principal import RoleNeed, UserNeed
from invenio_access import action_factory
from invenio_access.permissions import Permission
from invenio_records_permissions.generators import AuthenticatedUser, Generator
from invenio_search.engine import dsl

archiver_read_all_role = RoleNeed("archiver-read-all")
archiver_notification_role = RoleNeed("archiver-notification")

clc_sync_action = action_factory("clc-sync")
clc_sync_permission = Permission(clc_sync_action)


class CERNEmailsGroups(Generator):
    """Allows by CERN emails or groups."""

    def __init__(self, config_key_emails=None, config_key_groups=None):
        """Constructors."""
        self._config_key_emails = config_key_emails
        self._config_key_groups = config_key_groups

    def _get_emails(self):
        """Get configured allowed emails."""
        return (
            current_app.config.get(self._config_key_emails, [])
            if self._config_key_emails
            else []
        )

    def _get_groups(self):
        """Get configured allowed groups."""
        return (
            current_app.config.get(self._config_key_groups, [])
            if self._config_key_groups
            else []
        )

    def needs(self, **kwargs):
        """Enabling Needs."""
        emails = [UserNeed(user_email) for user_email in self._get_emails()]
        groups = [RoleNeed(group_name) for group_name in self._get_groups()]
        return emails + groups

    def query_filter(self, **kwargs):
        """Match all in search."""
        raise NotImplementedError


class AuthenticatedRegularUser(AuthenticatedUser):
    """Generator for regular users. Excludes robot accounts."""

    def excludes(self, **kwargs):
        """Exclude service/robot accounts."""
        excludes = super().excludes(**kwargs)
        return excludes + [archiver_read_all_role, archiver_notification_role]


class ArchiverRole(Generator):
    """Base generator class to define Archiver roles."""

    @property
    def archiver_role(self):
        """Role property."""
        raise NotImplementedError()

    def needs(self, **kwargs):
        """Enabling Needs."""
        return [self.archiver_role]

    def query_filter(self, identity=None, **kwargs):
        """Filters for current identity as system process."""
        for need in identity.provides:
            if need == self.archiver_role:
                return dsl.Q("match_all")
        else:
            return []


class ArchiverRead(ArchiverRole):
    """Allows by archiver_read_all role."""

    @property
    def archiver_role(self):
        """Role property."""
        return archiver_read_all_role


class ArchiverNotification(ArchiverRole):
    """Allows by archiver_notification role."""

    @property
    def archiver_role(self):
        """Role property."""
        return archiver_notification_role


class Librarian(Generator):
    """Allows librarian role."""

    def needs(self, **kwargs):
        """Enabling Needs."""
        return [clc_sync_action]
