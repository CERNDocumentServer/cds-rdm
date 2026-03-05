# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Draft lifecycle management module."""

from flask import current_app
from invenio_access.permissions import system_identity
from invenio_db import db
from invenio_rdm_records.proxies import current_rdm_records_service
from invenio_rdm_records.services.errors import ValidationErrorWithMessageAsList
from invenio_vocabularies.datastreams.errors import WriterError
from marshmallow import ValidationError


class DraftLifecycleManager:
    """Manages draft creation, editing, versioning, and publishing."""

    def create(self, entry):
        """Create a new draft from entry data."""
        return current_rdm_records_service.create(system_identity, data=entry)

    def edit(self, record_pid):
        """Open an edit draft for an existing published record."""
        return current_rdm_records_service.edit(system_identity, record_pid)

    def new_version(self, record_pid):
        """Create a new-version draft from an existing published record."""
        return current_rdm_records_service.new_version(system_identity, record_pid)

    def add_community(self, draft):
        """Add the CERN Scientific Community to the draft."""
        with db.session.begin_nested():
            community_id = current_app.config["CDS_CERN_SCIENTIFIC_COMMUNITY_ID"]
            draft_obj = current_rdm_records_service.draft_cls.pid.resolve(
                draft.id, registered_only=False
            )
            draft_obj.parent.communities.add(community_id)
            draft_obj.parent.communities.default = community_id
            draft_obj.parent.commit()

    def publish(self, draft_id, logger):
        """Publish a draft. Deletes the draft on any failure, then raises WriterError."""
        try:
            logger.debug(f"Publishing draft {draft_id}")
            current_rdm_records_service.publish(system_identity, draft_id)
            logger.info(f"Draft {draft_id} published successfully.")
        except ValidationError as e:
            logger.error(
                f"Failure: draft {draft_id} not published, validation errors: {e}."
            )
            current_rdm_records_service.delete_draft(system_identity, draft_id)
            raise WriterError(
                f"Failure: draft {draft_id} not published, validation errors: {e}."
            )
        except ValidationErrorWithMessageAsList as e:
            current_rdm_records_service.delete_draft(system_identity, draft_id)
            raise WriterError(
                f"Failure: draft {draft_id} not published,"
                f" validation errors: {e.messages}."
            )
        except Exception as e:
            current_rdm_records_service.delete_draft(system_identity, draft_id)
            raise WriterError(
                f"Draft {draft_id} failed publishing"
                f" because of an unexpected error: {str(e)}."
            )
