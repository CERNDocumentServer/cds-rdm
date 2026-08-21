# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Draft lifecycle management module."""

from flask import current_app
from invenio_db import db
from invenio_rdm_records.proxies import current_rdm_records_service
from invenio_rdm_records.services.errors import ValidationErrorWithMessageAsList
from invenio_vocabularies.datastreams.errors import WriterError
from marshmallow import ValidationError

from cds_rdm.inspire_harvester.logger import (
    format_validation_error,
    raise_unexpected_operation_error,
)


class DraftLifecycleManager:
    """Manages draft creation, editing, versioning, and publishing."""

    def __init__(self, identity):
        """Constructor."""
        self.identity = identity

    def create(self, entry):
        """Create a new draft from entry data."""
        return current_rdm_records_service.create(self.identity, data=entry)

    def edit(self, record_pid):
        """Open an edit draft for an existing published record."""
        return current_rdm_records_service.edit(self.identity, record_pid)

    def update(self, draft, metadata):
        """Update draft."""
        return current_rdm_records_service.update_draft(
            self.identity, draft.id, metadata
        )

    def new_version(self, record_pid):
        """Create a new-version draft from an existing published record."""
        return current_rdm_records_service.new_version(self.identity, record_pid)

    def add_cern_research_community(self, draft):
        """Add the CERN Scientific Community to the draft."""
        with db.session.begin_nested():
            community_id = current_app.config["CDS_CERN_SCIENTIFIC_COMMUNITY_ID"]
            draft_obj = current_rdm_records_service.draft_cls.pid.resolve(
                draft.id, registered_only=False
            )
            draft_obj.parent.communities.add(community_id)
            draft_obj.parent.communities.default = community_id
            draft_obj.parent.commit()

    def delete_files(self, draft_id, filenames, logger):
        """Delete files from a draft."""
        for filename in filenames:
            logger.debug(f"Delete file: {filename}")
            current_rdm_records_service.draft_files.delete_file(
                self.identity, draft_id, filename
            )

    def publish(self, draft_id, logger):
        """Publish a draft. Deletes the draft on any failure, then raises WriterError."""
        try:
            logger.debug(f"Publishing draft {draft_id}")
            current_rdm_records_service.publish(self.identity, draft_id)
            logger.info(f"Draft {draft_id} published successfully.")
        except (ValidationError, ValidationErrorWithMessageAsList) as e:
            current_rdm_records_service.delete_draft(self.identity, draft_id)
            raise WriterError(
                f"Record validation failed: {format_validation_error(e)}"
            ) from e
        except Exception as e:
            current_rdm_records_service.delete_draft(self.identity, draft_id)
            raise_unexpected_operation_error(
                subject="draft",
                action="published",
                error=e,
                logger=logger,
                draft_id=draft_id,
            )
