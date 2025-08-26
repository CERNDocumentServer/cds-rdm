# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the GPL-2.0 License; see LICENSE file for more details.

"""CDS-RDM exceptions."""

from invenio_i18n import lazy_gettext as _


class GroupSyncingError(Exception):
    """Group base syncing exception."""


class RequestError(GroupSyncingError):
    """The provided set spec does not exist."""

    def __init__(self, url, error_details):
        """Initialise error."""
        super().__init__(_(f"Request error on {url}.\n Error details: {error_details}"))


class KeycloakIdentityNotFoundError(Exception):
    def __init__(self, user_id: str) -> None:
        super().__init__(_(f"Could not find CERN SSO identity for user {user_id}"))


class GitLabIdentityNotFoundError(Exception):
    def __init__(self, user_id: str) -> None:
        super().__init__(_(f"GitLab user {user_id} did not have CERN SSO identity"))


class KeycloakGitLabMismatchError(Exception):
    def __init__(
        self,
        gitlab_user_id: str,
        gl_cern_sso_id: str,
        cds_user_id: str,
        cds_cern_sso_id: str,
    ) -> None:
        super().__init__(
            _(
                f"GitLab user {gitlab_user_id} has a different CERN SSO identity ({gl_cern_sso_id}) to currently signed-in CDS user {cds_user_id} ({cds_cern_sso_id})"
            )
        )
