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


@shared_task()
def create_community_inclusion_request(record_id):
    """Create a community inclusion request for ."""
    # Create a community-inclusion request
    sis_community_id = current_app.config.get("CDS_CERN_SCIENTIFIC_COMMUNITY")
    data = dict(
        communities=[
            {
                "id": sis_community_id,
                "require_review": True,
            }
        ]
    )

    current_rdm_records.record_communities_service.add(system_identity, record_id, data)


class CDSResourcePublication(ServiceComponent):
    """CDS resource publication component.

    - Thesis (resource type: ``publication-thesis``):
        - if no community selected, then raise Validation error to enforce selection of `CERN Scientific Community`
    - Public record and research resource tpe (e.g ``publication``):
        - if no community selected, create
    """

    def publish(self, identity, draft=None, record=None, **kwargs):
        """Update draft metadata."""

        sis_community = current_communities.service.read(
            identity, current_app.config.get("CDS_CERN_SCIENTIFIC_COMMUNITY")
        )
        resource_type = draft.get("metadata", {}).get("resource_type", {}).get("id")
        request_receiver = (
            draft.get("parent", {}).get("review", {}).get("community", {}).get("id")
        )
        is_record_public = draft["access"]["record"] == "public"

        if resource_type == "publication-thesis":
            if (
                request_receiver is None
                and sis_community.id not in draft.parent.communities.ids
            ):
                # create review request
                error_message = {
                    "field": "metadata.resource_type",
                    "messages": [
                        _(
                            "The publication-thesis resource type must be published in the "
                            f"'{sis_community.data['metadata']['title']}'. Please select the community from the top header and submit the publication for review."
                        )
                    ],
                }
                raise ValidationErrorWithMessageAsList(message=[error_message])
        elif is_record_public and resource_type.startswith("publication"):
            if (
                request_receiver is None
                and sis_community.id not in draft.parent.communities.ids
            ):
                self.uow.register(
                    TaskOp.for_async_apply(
                        create_community_inclusion_request, args=(record["id"],)
                    )
                )
