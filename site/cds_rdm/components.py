# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2025 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""CDS RDM service components."""

from celery import shared_task
from flask import current_app
from invenio_access.permissions import system_identity
from invenio_communities.proxies import current_communities
from invenio_drafts_resources.services.records.components import ServiceComponent
from invenio_i18n import lazy_gettext as _

from invenio_rdm_records.services.errors import ValidationErrorWithMessageAsList
from invenio_rdm_records.proxies import current_rdm_records
from invenio_records_resources.services.uow import TaskOp


# @shared_task()
# def create_community_inclusion_request(record_id):
#     """Create a community inclusion request for ."""
#     # Create a community-inclusion request
#     csc_community_id = current_app.config.get("CDS_CERN_SCIENTIFIC_COMMUNITY_ID")
#     data = dict(
#         communities=[
#             {
#                 "id": csc_community_id,
#                 "require_review": True,
#             }
#         ]
#     )

#     current_rdm_records.record_communities_service.add(system_identity, record_id, data)


def is_record_public(record):
    """Check if the record is public."""
    return record["access"]["record"] == "public"


def is_thesis(record):
    """Check if the record is a thesis."""
    resource_type = record["metadata"].get("resource_type", {}).get("id")
    return resource_type == "publication-thesis"


class CDSResourcePublication(ServiceComponent):
    """CDS resource publication component."""

    def _validate_thesis_community(self, identity, record_or_draft, errors=None):
        """Validate that a thesis is associated with the CERN Scientific Community."""
        csc_community = current_communities.service.read(
            identity, current_app.config.get("CDS_CERN_SCIENTIFIC_COMMUNITY_ID")
        )

        request_receiver = (
            record_or_draft.parent.review is not None
            and record_or_draft.parent.review.receiver.reference_dict.get("community")
        )

        if not request_receiver or request_receiver != csc_community.id:
            error_message = {
                "field": "metadata.resource_type",
                "messages": [
                    _(
                        "Thesis must be published in the "
                        f"'{csc_community.data['metadata']['title']}'. Please select the community from the top header and submit the publication for review."
                    )
                ],
            }
            if errors is not None:
                errors.append(error_message)
            else:
                raise ValidationErrorWithMessageAsList(message=[error_message])

    def create(self, identity, data=None, record=None, errors=None, **kwargs):
        """Create draft metadata."""
        if is_thesis(record):
            self._validate_thesis_community(identity, record, errors)

    def update_draft(self, identity, data=None, record=None, errors=None):
        """Update draft metadata."""
        if is_thesis(record):
            self._validate_thesis_community(identity, record, errors)

    def publish(self, identity, draft=None, record=None, **kwargs):
        """Publish draft metadata."""

        if is_thesis(draft):
            self._validate_thesis_community(identity, draft, errors=None)
        # elif is_record_public(record) and resource_type.startswith("publication"):
        #     if (
        #         request_receiver is None
        #         and csc_community.id not in draft.parent.communities.ids
        #     ):
        #         self.uow.register(
        #             TaskOp.for_async_apply(
        #                 create_community_inclusion_request, args=(record["id"],)
        #             )
        #         )
