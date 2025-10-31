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
from sqlalchemy import and_, or_

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
    """Service component for minting alternative identifiers."""

    def create(self, identity, data=None, record=None, errors=None, **kwargs):
        """Mint/update alternative identifiers on create."""
        alt_id_schemes = current_app.config["CDS_CERN_MINT_ALTERNATE_IDS"]
        # The schema validation ensures that the identifiers are unique by scheme, so we can use a set to avoid duplicates
        identifiers_to_mint = {}
        for index, id in enumerate(data["metadata"].get("identifiers", [])):
            if id["scheme"] in alt_id_schemes:
                identifiers_to_mint[(id["scheme"], id["identifier"])] = index

        if not identifiers_to_mint:
            # If no mintable identifiers, return early
            return

        # Query the DB to check if the identifier already exist
        existing_pids = PersistentIdentifier.query.filter(
            PersistentIdentifier.object_type == "rec",
            or_(
                *[
                    and_(
                        PersistentIdentifier.pid_type == pid_type,
                        PersistentIdentifier.pid_value == pid_value,
                    )
                    for pid_type, pid_value in identifiers_to_mint.keys()
                ]
            ),
        ).all()

        def already_exists_error_message(scheme, value, index):
            """Return the error message for a duplicate identifier."""
            return {
                "field": f"metadata.identifiers.{index}.identifier",
                "messages": [
                    _(
                        f"Identifier value '{value}' for scheme '{alt_id_schemes[scheme]}' already exists."
                    )
                ],
            }

        for pid in existing_pids:
            # Remove the identifier from the list of identifiers to mint as RESERVED
            index = identifiers_to_mint.pop((pid.pid_type, pid.pid_value))
            if pid.object_uuid == record.parent.id:
                # The identifier already exists in the record, or in another version, so we can skip it
                continue
            # Otherwise, raise an error because the identifier is already used by another record
            errors.append(
                already_exists_error_message(pid.pid_type, pid.pid_value, index)
            )

        # Mint the identifiers that are not already used by another record
        for (pid_type, pid_value), index in identifiers_to_mint.items():
            try:
                PersistentIdentifier.create(
                    pid_type=pid_type,
                    pid_value=pid_value,
                    object_type="rec",
                    object_uuid=record.parent.id,
                    status=PIDStatus.RESERVED,
                )
            except (
                PIDAlreadyExists
            ):  # Make sure the operation on te draft is not blocked
                errors.append(already_exists_error_message(pid_type, pid_value, index))

    def edit(self, identity, draft=None, record=None):
        """Mint/update alternative identifiers on edit."""
        return self.create(identity, data=draft, record=record)

    def update_draft(self, identity, data=None, record=None, errors=None):
        """Mint/update alternative identifiers on update."""
        return self.create(identity, data=data, record=record, errors=errors)

    def new_version(self, identity, draft=None, record=None):
        """Mint/update alternative identifiers on new version."""
        return self.create(identity, data=draft, record=record)

    def publish(self, identity, draft=None, record=None):
        """Sync minted alternative identifiers with the record family's alternate identifiers on publish."""
        self.uow.register(TaskOp(sync_alternate_identifiers, str(record.parent.id)))
