# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Draft lifecycle management module."""

from flask import current_app
from invenio_db import db
from invenio_drafts_resources.services.records.uow import ParentRecordCommitOp
from invenio_rdm_records.proxies import current_rdm_records_service
from invenio_rdm_records.services.errors import ValidationErrorWithMessageAsList
from invenio_records_resources.services.uow import RecordCommitOp, UnitOfWork
from invenio_vocabularies.datastreams.errors import WriterError
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from cds_rdm.inspire_harvester.logger import (
    format_validation_error,
    raise_unexpected_operation_error,
)


def _remint_recid(obj, new_pid_value, uow):
    """Swap the auto-minted recid for the one from prod.

    Create always mints fresh parent/version ids. On sandbox we overwrite
    those values so the sandbox record keeps the same ids as prod.

    After resolve, ``obj.pid`` may be rebuilt from the record JSON and not
    sit in the DB session. Merge it first so we UPDATE the real row instead
    of INSERTing a second one (that looks like "pid already exists").
    """
    # pid from JSON is transient until merged into the session
    type(obj).pid.session_merge(obj)
    pid = obj.pid
    try:
        with uow.session.begin_nested():
            pid.pid_value = new_pid_value
            uow.session.add(pid)
    except IntegrityError as exc:
        raise WriterError(
            "Cannot reuse CDSRDM recid - already exists. "
            f"| details: pid={new_pid_value}"
        ) from exc
    # Tell the PID field to write the new id into the record JSON as well.
    obj.pid = pid


class DraftLifecycleManager:
    """Manages draft creation, editing, versioning, and publishing."""

    def __init__(self, identity):
        """Constructor."""
        self.identity = identity

    def create(self, entry):
        """Create a new draft from entry data."""
        return current_rdm_records_service.create(self.identity, data=entry)

    def create_reusing_prod_pids(self, entry, parent_pid, record_pid):
        """Create a draft and keep prod's parent and version ids.

        Even one published version has two ids: a parent and a
        version. We create normally, then replace both auto-minted
        ids with the ones from prod, in one unit of work so it is atomic.
        """
        with UnitOfWork() as uow:
            draft = current_rdm_records_service.create(
                self.identity, data=entry, uow=uow
            )
            draft_obj = current_rdm_records_service.draft_cls.pid.resolve(
                draft.id, registered_only=False
            )
            # Parent first, then the version/record id.
            _remint_recid(draft_obj.parent, parent_pid, uow)
            uow.register(ParentRecordCommitOp(draft_obj.parent))
            _remint_recid(draft_obj, record_pid, uow)
            uow.register(RecordCommitOp(draft_obj))
            uow.commit()

        # Return the draft under the reminted version id.
        return current_rdm_records_service.read_draft(self.identity, record_pid)

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
