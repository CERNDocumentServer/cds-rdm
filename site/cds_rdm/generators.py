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
from invenio_access.permissions import Permission, system_identity
from invenio_rdm_records.services.generators import AccessGrant
from invenio_records_permissions.generators import AuthenticatedUser, Generator
from invenio_records_resources.services.errors import PermissionDeniedError
from invenio_search.engine import dsl
from invenio_users_resources.proxies import current_users_service

from .administration.permissions import harvester_admin_access_action

archiver_read_all_role = RoleNeed("archiver-read-all")
archiver_notification_role = RoleNeed("archiver-notification")
inspire_harvester_role = RoleNeed("inspire-harvester")

clc_sync_action = action_factory("clc-sync")
clc_sync_permission = Permission(clc_sync_action)

allow_metadata_only_action = action_factory("allow-metadata-only")


def _harvester_user_id():
    """Resolve configured harvester user id via the users service."""
    email = current_app.config.get("CDS_HARVESTER_USER_EMAIL")
    if not email:
        return None
    try:
        user = current_users_service.read(system_identity, email=email)
    except PermissionDeniedError:
        return None
    return str(user.id)


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
        return excludes + [
            archiver_read_all_role,
            archiver_notification_role,
        ]


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


class InspireHarvester(Generator):
    """Allows by inspire-harvester role."""

    def needs(self, **kwargs):
        """Enabling Needs."""
        return [inspire_harvester_role]


class HarvesterCurator(Generator):
    """Allows harvester curators via the harvester admin action."""

    def needs(self, **kwargs):
        """Enabling Needs."""
        return [harvester_admin_access_action]

    def query_filter(self, identity=None, **kwargs):
        """Filter to harvester and legacy system publish audit logs."""
        if identity and Permission(harvester_admin_access_action).allows(identity):
            user_ids = ["system"]
            harvester_user_id = _harvester_user_id()
            if harvester_user_id is not None:
                user_ids.append(harvester_user_id)

            return dsl.Q(
                "bool",
                must=[
                    dsl.Q("terms", **{"user.id": user_ids}),
                    dsl.Q("term", action="record.publish"),
                ],
            )
        return []


class Librarian(Generator):
    """Allows librarian role."""

    def needs(self, **kwargs):
        """Enabling Needs."""
        return [clc_sync_action]


class AllowMetadataOnlyForCurators(Generator):
    """Allows metadata-only-curator role."""

    def needs(self, **kwargs):
        """Enabling Needs."""
        return [allow_metadata_only_action]


class EPWorkflowCommunityManager(Generator):
    """Allows community managers of EP-workflow-enrolled communities.

    A community is enrolled by having its UUID listed as a key in the
    ``CDS_COMMITTEE_APPROVAL_COMMUNITIES`` config dict.
    """

    def needs(self, record=None, **kwargs):
        """Return needs for all enrolled communities' manager roles.

        The record's parent communities are intersected with the config to find
        the relevant community, then we require the community-manager role need.
        """
        from invenio_communities.generators import CommunityRoleNeed

        ep_communities = current_app.config.get(
            "CDS_COMMITTEE_APPROVAL_COMMUNITIES", {}
        )
        if record is None:
            return []

        default_community_id = record.parent.get("communities", {}).get("default")
        needs = []
        if default_community_id in ep_communities:
            needs.append(CommunityRoleNeed(default_community_id, "manager"))
            needs.append(CommunityRoleNeed(default_community_id, "owner"))
        return needs

    def query_filter(self, **kwargs):
        """Not used for search filters."""
        return []


COMMITTEE_APPROVAL_GRANT_ORIGIN_PREFIX = "committee-approval:"
COMMITTEE_APPROVAL_GRANT_PERMISSION = "committee-review"
COMMITTEE_APPROVAL_ACCESS_GRANT = AccessGrant(COMMITTEE_APPROVAL_GRANT_PERMISSION)


def committee_approval_grant_origin(record_pid: str, version_index: int):
    """Return the grant origin string for a specific record version index."""
    return f"{COMMITTEE_APPROVAL_GRANT_ORIGIN_PREFIX}{record_pid}_{version_index}"


def get_version_index_from_origin(origin: str):
    """Returns just the version index number from the grant origin."""
    id_and_version_str = origin.removeprefix(COMMITTEE_APPROVAL_GRANT_ORIGIN_PREFIX)
    components = id_and_version_str.split("_")
    if len(components) != 2:
        return None
    _, version_str = components
    if not version_str.isdigit():
        return None
    return int(version_str)


class CommitteeRefereeVersionGrant(Generator):
    """Read access for committee referees scoped to the exact version they reviewed, as well as newer versions created after the approval was granted.

    Later versions than the one for which the review was requested are only be accessible
    if they were created after the review was approved.

    On submit  → grant added (version UUID = topic.id at submit time).
    On accept  → grant kept; referees retain permanent access to that version.
    On decline / cancel → grant removed.
    """

    def needs(self, record=None, **kwargs):
        """Return the RoleNeed if this version has a matching committee review grant."""
        if record is None:
            return []

        needs = []
        for grant in record.parent.access.grants:
            if grant.permission != COMMITTEE_APPROVAL_GRANT_PERMISSION:
                continue

            grant_version = get_version_index_from_origin(grant.origin)
            if grant_version is not None and record.versions.index >= grant_version:
                needs.append(grant.to_need())

        return needs

    def query_filter(self, identity=None, **kwargs):
        """Filter for records with a committee review grant for one of the identity's roles."""
        return COMMITTEE_APPROVAL_ACCESS_GRANT.query_filter(identity, kwargs=kwargs)
