# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2025 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""CDS RDM service components."""

from flask import current_app
from invenio_communities.proxies import current_communities
from invenio_drafts_resources.services.records.components import ServiceComponent
from invenio_i18n import gettext as _
from invenio_i18n import lazy_gettext as _
from invenio_pidstore.errors import PIDAlreadyExists
from invenio_pidstore.models import PersistentIdentifier, PIDStatus
from invenio_records_resources.services.uow import TaskOp
from marshmallow import ValidationError

from .tasks import sync_alternate_identifiers

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
    resource_type = record["metadata"]["resource_type"]["id"]
    return resource_type == "publication-dissertation"  # Previously publication-thesis


class CDSResourcePublication(ServiceComponent):
    """CDS resource publication component."""

    def _validate_thesis_community(self, identity, record_or_draft, errors=None):
        """Validate that a thesis is associated with the CERN Scientific Community."""
        csc_community = current_communities.service.read(
            identity, current_app.config["CDS_CERN_SCIENTIFIC_COMMUNITY_ID"]
        )

        if csc_community.id in record_or_draft.parent["communities"].get("ids", []):
            return

        request_receiver = (
            record_or_draft.parent.review is not None
            and record_or_draft.parent.review.receiver.reference_dict.get("community")
        )

        if not request_receiver or request_receiver != csc_community.id:
            error_message = _(
                "Thesis must be published in the "
                f"'{csc_community.data['metadata']['title']}' community. Please select the community from the top header and submit the thesis for review."
            )

            if errors is not None:
                errors.append(error_message)
            else:
                raise ValidationError(message=error_message)

    def publish(self, identity, draft=None, record=None, **kwargs):
        """Publish draft metadata."""
        if is_thesis(draft):
            self._validate_thesis_community(identity, draft, errors=None)

    def submit_record(self, identity, data=None, record=None, **kwargs):
        """Submit draft metadata for review."""
        if is_thesis(record):
            self._validate_thesis_community(identity, record, errors=None)


class SubjectsValidationComponent(ServiceComponent):
    """Service component for subjects validation.

    To be used with records which were formerly in multiple collections on CDS (legacy).
    We tag those records with subject `collection:<collection name>` to be able to retrieve them in the future.
    those subjects should not be modifiable by a regular user.
    """

    def _validate_subject_changes(self, identity, updated_data, original_data):
        """Validate that the subject changes are allowed."""
        user = getattr(identity, "user", None)
        if user and user.has_role("administration"):
            return
        updated_collection_subjects = {
            s["subject"]
            for s in updated_data
            if s.get("subject", "").startswith("collection:")
        }
        original_collection_subjects = {
            s["subject"]
            for s in original_data
            if s.get("subject", "").startswith("collection:")
        }
        if updated_collection_subjects != original_collection_subjects:
            raise ValidationError(
                "Collection subjects cannot be updated.",
                field_name="metadata.subjects",
            )

    def update_draft(self, identity, data=None, record=None, **kwargs):
        """Validate subject changes on update."""
        self._validate_subject_changes(
            identity,
            data["metadata"].get("subjects", []),
            record.get("metadata", {}).get("subjects", []),
        )

    def publish(self, identity, draft=None, record=None, **kwargs):
        """Validate subject changes on publish."""
        self._validate_subject_changes(
            identity,
            draft.metadata.get("subjects", []),
            record.get("metadata", {}).get("subjects", []),
        )


class MintAlternateIdentifierComponent(ServiceComponent):
    """Service component for minting alternative identifier `CDS Report Number`."""

    def create(self, identity, data=None, record=None, errors=None, **kwargs):
        """Mint/update alternative identifiers on create."""
        draft_report_nums = {}
        for index, id in enumerate(data["metadata"].get("identifiers", [])):
            if id["scheme"] == "cdsrn":
                draft_report_nums[id["identifier"]] = index

        if not draft_report_nums:
            # If no mintable identifiers, return early
            return

        # Query the DB to check if the identifier already exist
        existing_report_nums = PersistentIdentifier.query.filter(
            PersistentIdentifier.pid_type == "cdsrn",
            PersistentIdentifier.object_uuid == record.parent.id,
        ).all()

        for report_number_pid in existing_report_nums:
            # Remove the identifier (if it still exists in the metadata) from the list of identifiers to mint as it already minted
            draft_report_nums.pop(report_number_pid.pid_value, None)

        # Check if the remaining identifiers are already taken by another record
        already_taken_report_nums = PersistentIdentifier.query.filter(
            PersistentIdentifier.pid_type == "cdsrn",
            PersistentIdentifier.pid_value.in_(list(draft_report_nums.keys())),
        ).all()
        # Doing this will decrease the number of queries to the database as we are not trying to insert the identifiers that are already taken by another record
        for report_number_pid in already_taken_report_nums:
            index = draft_report_nums[report_number_pid.pid_value]
            errors.append(
                {
                    "field": f"metadata.identifiers.{index}.identifier",
                    "messages": [
                        _(
                            f"The CDS report number '{report_number_pid.pid_value}' is already taken. Please choose a different one."
                        )
                    ],
                }
            )
            draft_report_nums.pop(report_number_pid.pid_value, None)

        # Mint the identifiers that are not already used by another record
        for report_number, index in draft_report_nums.items():
            try:
                PersistentIdentifier.create(
                    pid_type="cdsrn",
                    pid_value=report_number,
                    object_type="rec",
                    object_uuid=record.parent.id,
                    status=PIDStatus.RESERVED,
                )
            except PIDAlreadyExists:
                # Make sure the operation on the draft is not blocked, it should never happen since we check for duplicates above
                errors.append(
                    {
                        "field": f"metadata.identifiers.{index}.identifier",
                        "messages": [
                            _(
                                f"The CDS report number '{report_number}' is already taken. Please choose a different one."
                            )
                        ],
                    }
                )

    def edit(self, identity, draft=None, record=None, errors=None):
        """Mint/update alternative identifiers on edit."""
        return self.create(identity, data=draft, record=record, errors=errors)

    def update_draft(self, identity, data=None, record=None, errors=None):
        """Mint/update alternative identifiers on update."""
        return self.create(identity, data=data, record=record, errors=errors)

    def new_version(self, identity, draft=None, record=None, errors=None):
        """Mint/update alternative identifiers on new version."""
        return self.create(identity, data=draft, record=record, errors=errors)

    def publish(self, identity, draft=None, record=None):
        """Sync minted alternative identifiers with the record family's alternate identifiers on publish."""
        self.uow.register(
            TaskOp(
                sync_alternate_identifiers,
                parent_id=str(record.parent.id),
                record_id=str(record.id),
            )
        )
