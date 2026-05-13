# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the GPL-2.0 License; see LICENSE file for more details.
"""Override the policy for whether new record versions require community review."""

from flask import current_app
from invenio_rdm_records.services.review import NewRecordVersionReviewPolicy


class CDSRecordVersionReviewPolicy(NewRecordVersionReviewPolicy):
    """Policy override."""

    @classmethod
    def requires_review(cls, identity, draft) -> bool:
        """Returns whether the new record version requires review."""
        default_community = draft.parent.communities.default
        if default_community is None:
            return False

        communities_requiring_new_record_version_review = current_app.config.get(
            "CDS_COMMUNITIES_REQUIRING_NEW_RECORD_VERSION_REVIEW", []
        )
        return (
            str(default_community.id) in communities_requiring_new_record_version_review
        )
