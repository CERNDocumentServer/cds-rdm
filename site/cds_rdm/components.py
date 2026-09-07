# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2025 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""CDS RDM service components."""

from flask import current_app
from invenio_access.permissions import system_user_id
from invenio_communities.proxies import current_communities
from invenio_drafts_resources.services.records.components import ServiceComponent
from invenio_i18n import gettext as _
from invenio_i18n import lazy_gettext as _
from invenio_pidstore.errors import PIDAlreadyExists
from invenio_pidstore.models import PersistentIdentifier, PIDStatus
from invenio_rdm_records.services.errors import ValidationErrorWithMessageAsList
from invenio_records_resources.services.uow import TaskOp
from marshmallow import ValidationError

from .tasks import (
    sync_alternate_identifiers,  # submit_community_inclusion_request temporarily disabled
)


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
        allowed_community_ids = [
            current_app.config["CDS_CERN_SCIENTIFIC_COMMUNITY_ID"],
            current_app.config["CDS_CERN_RELATED_RESEARCH_COMMUNITY_ID"],
        ]

        for community_id in record_or_draft.parent["communities"].get("ids", []):
            if community_id in allowed_community_ids:
                return

        request_receiver = (
            record_or_draft.parent.review is not None
            and record_or_draft.parent.review.receiver.reference_dict.get("community")
        )

        if not request_receiver or request_receiver not in allowed_community_ids:
            community_titles = []
            for community_id in allowed_community_ids:
                community = current_communities.service.read(identity, community_id)
                community_titles.append(community.data["metadata"]["title"])

            error_message = _(
                "Theses must be published in one of the following communities: "
                f"{', '.join(community_titles)}. Please select the community from the top header and submit the thesis for review."
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
        if identity.id == "system" or user and user.has_role("administration"):
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


class CommitteeApprovalComponent(ServiceComponent):
    """Guard and sync committee approval identifiers.

    1. Blocks everyone except the system process from adding/modifying/deleting
       ``apprn`` scheme identifiers — including admins via the UI.
    2. Regenerates the ``apprn`` metadata identifier from parent committee_approval
       only when ``source_internal_version`` is set on the parent.  This covers
       two cases:
         - Public approved copy in the two-record flow (views.py sets
           ``source_internal_version`` to the internal record's recid).
         - Single-record migration case (migrate_cdsrn_to_apprn.py sets
           ``source_internal_version`` to the record's own recid).
       The internal record in the normal flow never has ``source_internal_version``
       on its parent, so it never carries the apprn identifier.
    """

    def _committee_approval_prefixes(self):
        """Return the set of fixed prefixes from all configured committee communities.

        E.g. config ``{"prefix": "CERN-EP"}`` → prefix ``"CERN-EP"``.
        Used to detect cdsrn values that collide with committee report numbers.
        """
        communities = current_app.config.get("CDS_COMMITTEE_APPROVAL_COMMUNITIES", {})
        prefixes = set()
        for cfg in communities.values():
            prefix = cfg.get("report_number", {}).get("prefix")
            if prefix:
                prefixes.add(prefix)
        return prefixes

    def _validate_identifier_changes(self, identity, data, record, errors):
        """Raise ValidationError if a non-system identity modifies apprn."""
        if identity.id == system_user_id:
            return

        incoming_identifiers = (data.get("metadata") or {}).get("identifiers", [])
        stored_identifiers = (record.get("metadata") or {}).get("identifiers", [])

        # Index stored apprn values for comparison.
        stored_apprn = {
            i["identifier"] for i in stored_identifiers if i.get("scheme") == "apprn"
        }
        incoming_apprn = {
            i["identifier"] for i in incoming_identifiers if i.get("scheme") == "apprn"
        }
        if incoming_apprn != stored_apprn:
            error_msg = _(
                "The approval report number is system-managed and cannot be "
                "added, modified, or removed manually."
            )

            errors = [
                {
                    "field": f"metadata.identifiers.{index}.identifier",
                    "messages": [error_msg],
                }
                for index, i in enumerate(incoming_identifiers)
                if i.get("scheme") == "apprn"
            ]

            if not errors:
                # apprn was removed — point to the field without a specific index
                errors = [
                    {
                        "field": "metadata.identifiers",
                        "messages": [error_msg],
                    }
                ]

            raise ValidationErrorWithMessageAsList(errors)

        # Block cdsrn values that look like committee report numbers.
        ep_prefixes = self._committee_approval_prefixes()
        if ep_prefixes:
            errors = []
            for index, ident in enumerate(incoming_identifiers):
                if ident.get("scheme") == "cdsrn":
                    val = ident.get("identifier", "")
                    if any(val.startswith(p) for p in ep_prefixes):
                        errors.append(
                            {
                                "field": f"metadata.identifiers.{index}.identifier",
                                "messages": [
                                    _(
                                        f"The value '{val}' matches an approval "
                                        "report number pattern and cannot be used as "
                                        "a CDS report number."
                                    )
                                ],
                            }
                        )
            if errors:
                raise ValidationErrorWithMessageAsList(errors)

    def _should_sync_apprn(self, record, committee_approval):
        """Return True if apprn should be synced with parent committee_approval."""
        reportnumber = committee_approval.get("reportnumber")
        source_internal = committee_approval.get("source_internal_version")
        if reportnumber and source_internal:
            return True
        return False

    def _regenerate_apprn_identifier(self, record, data):
        """Keep apprn in metadata.identifiers in sync with parent committee_approval.

        committee_approval.reportnumber is the source of truth (a list of strings).
        The metadata apprn entries are derived from it exactly — no other apprn
        entries are preserved.
        """
        committee_approval = (
            (record.parent.get("permission_flags") if record.parent else None) or {}
        ).get("committee_approval") or {}

        existing_identifiers = (data.get("metadata") or {}).get("identifiers", [])
        app_rn = [i for i in existing_identifiers if i.get("scheme") == "apprn"]
        not_apprn = [i for i in existing_identifiers if i.get("scheme") != "apprn"]

        if self._should_sync_apprn(record, committee_approval):
            reportnumbers = committee_approval.get("reportnumber") or []
            apprn = [{"scheme": "apprn", "identifier": rn} for rn in reportnumbers]
            new_identifiers = apprn + not_apprn
        else:
            # check if there are any remaining apprn identifiers and raise a validation error if they exist
            if app_rn:
                errors = [
                    {
                        "field": "metadata.identifiers",
                        "messages": [
                            _(
                                "The approval report number is system-managed and cannot be "
                                "added, modified, or removed manually.",
                            )
                        ],
                    }
                ]
                raise ValidationErrorWithMessageAsList(errors)
            new_identifiers = not_apprn

        data.setdefault("metadata", {})["identifiers"] = new_identifiers

    def create(self, identity, data=None, record=None, errors=None, **kwargs):
        """Validate apprn identifier on draft creation."""
        self._validate_identifier_changes(identity, data, record, errors)

    def update_draft(self, identity, data=None, record=None, errors=None, **kwargs):
        """Validate and regenerate apprn identifier on draft update."""
        self._validate_identifier_changes(identity, data, record, errors)
        self._regenerate_apprn_identifier(record, data)

    def publish(self, identity, draft=None, record=None, **kwargs):
        """Regenerate apprn identifier on publish.

        Validation is intentionally skipped here — publish does not accept
        user-supplied data, and create/update_draft already guard all entry
        points. The ``record`` argument at publish time is a newly created
        empty object (populated by later components), so comparing against it
        would produce false positives.
        """
        # draft is the RDMDraft API object (extends dict); pass it directly
        # so that modifications to metadata.identifiers are persisted.
        self._regenerate_apprn_identifier(draft, draft)


class MintAlternateIdentifierComponent(ServiceComponent):
    """Service component for minting alternative identifier `CDS Report Number`."""

    def _validate_alternative_identifiers(self, data=None, record=None, errors=None):
        """Validate alternative identifiers."""
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

    def update_draft(self, identity, data=None, record=None, errors=None):
        """Mint/update alternative identifiers on draft update."""
        self._validate_alternative_identifiers(data=data, record=record, errors=errors)

    def publish(self, identity, draft=None, record=None):
        """Sync minted alternative identifiers with the record family's alternate identifiers on publish."""
        errors = []
        self._validate_alternative_identifiers(data=draft, record=record, errors=errors)
        if errors:
            raise ValidationErrorWithMessageAsList(errors)
        self.uow.register(
            TaskOp(
                sync_alternate_identifiers,
                parent_id=str(record.parent.id),
                record_id=str(record.id),
            )
        )


# PublicationInclusionComponent temporarily disabled
# class PublicationInclusionComponent(ServiceComponent):
#     """Auto-submit a community inclusion request to the CERN Scientific Community.
#
#     Triggers on publish for public records whose resource type is listed in
#     `CDS_CERN_SCIENTIFIC_RESOURCE_TYPES`. The request is created asynchronously
#     after the publish transaction commits.
#     """
#
#     def _is_eligible(self, draft, record):
#         """Return True when the record should be auto-submitted for community inclusion."""
#         if not is_record_public(draft):
#             return False
#
#         resource_type = draft["metadata"]["resource_type"]["id"]
#         research_resource_types = current_app.config.get(
#             "CDS_CERN_SCIENTIFIC_RESOURCE_TYPES", set()
#         )
#         if resource_type not in research_resource_types:
#             return False
#
#         # Skip if the record is in the Scientific Community or the Related Research Community already
#         # IMPORTANT:
#         # 1. For thesis, we have the component CDSResourcePublication to validate the community selection
#         # 2. For other resource types, it is highly unlikely that the record is NOT eligible for inclusion
#         # in the CERN Research Community, since these works typically belong to CERN
#         # On the off chance if there is a rare case, it will be dealt via support on case by case basis
#         communities_to_skip = [
#             current_app.config["CDS_CERN_SCIENTIFIC_COMMUNITY_ID"],
#             current_app.config["CDS_CERN_RELATED_RESEARCH_COMMUNITY_ID"],
#         ]
#         for community_id in communities_to_skip:
#             if not community_id:
#                 current_app.logger.error(
#                     f"Scientific Community IDs are not configured; "
#                     "skipping auto community inclusion for record %s.",
#                     record.pid.pid_value,
#                 )
#                 return False
#             if community_id in record.parent.communities.ids:
#                 return False
#
#         return True
#
#     def publish(self, identity, draft=None, record=None, **kwargs):
#         """Schedule community inclusion request after the record is published."""
#         if not self._is_eligible(draft, record):
#             return
#
#         self.uow.register(
#             TaskOp(
#                 submit_community_inclusion_request,
#                 record_id=record.pid.pid_value,
#             )
#         )
