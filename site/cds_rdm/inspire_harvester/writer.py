# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Writer module."""

from copy import deepcopy

from flask import current_app
from invenio_access.permissions import system_identity

from cds_rdm.inspire_harvester.utils import compare_metadata
from invenio_rdm_records.proxies import current_rdm_records_service
from invenio_vocabularies.datastreams.errors import WriterError
from invenio_vocabularies.datastreams.writers import BaseWriter
from marshmallow import ValidationError

from cds_rdm.inspire_harvester.load.draft import DraftLifecycleManager
from cds_rdm.inspire_harvester.load.files import FileSynchronizer
from cds_rdm.inspire_harvester.logger import Logger, hlog
from cds_rdm.inspire_harvester.load.matcher import RecordMatcher
from cds_rdm.inspire_harvester.update.config import UPDATE_STRATEGY_CONFIG
from cds_rdm.inspire_harvester.update.engine import UpdateContext, UpdateEngine


class InspireWriter(BaseWriter):
    """INSPIRE writer — thin orchestrator delegating to focused components."""

    def __init__(self):
        """Constructor."""
        self.matcher = RecordMatcher()
        self.file_sync = FileSynchronizer()
        self.drafts = DraftLifecycleManager()

    def write(self, stream_entry, *args, **kwargs):
        """Create or update the record in CDS."""
        return self._process_entry(stream_entry)

    def write_many(self, stream_entries, *args, **kwargs):
        """Create or update records in CDS."""
        current_app.logger.debug(f"Start: write_many ({len(stream_entries)} entries)")
        for i, stream_entry in enumerate(stream_entries, 1):
            current_app.logger.debug(f"Processing entry {i}/{len(stream_entries)}")
            self.write(stream_entry)
        current_app.logger.info("All entries processed.")
        return stream_entries

    def _process_entry(self, stream_entry):
        """Process a single stream entry, catching expected errors."""
        inspire_id = stream_entry.entry["id"]
        logger = Logger(inspire_id=inspire_id)
        error_message = None
        op_type = None

        try:
            op_type = self._route(stream_entry)
        except WriterError as e:
            error_message = f"Error while processing entry : {str(e)}."
        except ValidationError as e:
            error_message = f"Validation error while processing entry: {str(e)}."

        if error_message:
            logger.error(error_message)
            stream_entry.errors.append(f"[inspire_id={inspire_id}] {error_message}")

        stream_entry.op_type = op_type
        return stream_entry

    @hlog
    def _route(self, stream_entry, inspire_id=None, record_pid=None, logger=None):
        """Route the entry to create or update based on existing record lookup."""
        entry = stream_entry.entry
        match_result = self.matcher.match(entry, inspire_id, logger)

        if match_result.ambiguous:
            msg = "Multiple records match: {0}".format(
                ", ".join(match_result.matched_ids)
            )
            logger.error(msg)
            stream_entry.errors.append(f"[inspire_id={inspire_id}] {msg}")
            return None

        elif match_result.found:
            logger.info(f"Matching record found: CDS#{match_result.record_pid}")
            self._update_record(stream_entry, record_pid=match_result.record_pid)
            return "update"

        else:
            self._create_record(stream_entry)
            return "create"

    @hlog
    def _update_record(self, stream_entry, record_pid=None, inspire_id=None, logger=None):
        """Dispatch to in-place edit or new-version based on file/DOI state."""
        entry = stream_entry.entry
        record = current_rdm_records_service.read(system_identity, record_pid)
        record_dict = record.to_dict()

        existing_files = record_dict["files"]["entries"]
        new_files = entry["files"].get("entries", {})
        logger.info(
            f"Existing files count: {len(existing_files)},"
            f" New files count: {len(new_files)}"
        )

        existing_checksums = [v["checksum"] for v in existing_files.values()]
        new_checksums = [v["checksum"] for v in new_files.values()]
        logger.debug(f"Existing files' checksums: {existing_checksums}.")
        logger.debug(f"New files' checksums: {new_checksums}.")

        should_update_files = bool(new_files) and existing_checksums != new_checksums

        # Enable files on the entry *before* the engine sees it so update_metadata carries it
        if should_update_files and not record_dict.get("files", {}).get("enabled", False):
            entry["files"]["enabled"] = True

        engine = UpdateEngine(strategies=UPDATE_STRATEGY_CONFIG, fail_on_conflict=True)
        result = engine.update(
            record_dict, entry, UpdateContext(source="inspire_import"), logger
        )
        update_metadata = result.updated

        has_cds_doi = record.data["pids"].get("doi", {}).get("provider") == "datacite"

        if should_update_files and has_cds_doi:
            self._publish_new_version(record, update_metadata, existing_files, new_files, logger)
        else:
            is_pids_equal = update_metadata["pids"] == record_dict["pids"]
            is_metadata_equal = compare_metadata(update_metadata["metadata"], record_dict["metadata"])
            is_custom_fields_equal = compare_metadata(update_metadata["custom_fields"], record_dict["custom_fields"])
            if is_pids_equal and is_metadata_equal and is_custom_fields_equal:
                logger.info(f"Skipping record, already up to date")
            else:
                self._publish_edit(
                    record_pid, update_metadata, should_update_files, existing_files, new_files, logger
                )

    def _publish_new_version(self, record, update_metadata, existing_files, new_files, logger):
        """Create and publish a new version with updated metadata and synced files."""
        draft = self.drafts.new_version(record["id"])

        new_version_entry = deepcopy(update_metadata)
        if "pids" in new_version_entry:
            del new_version_entry["pids"]

        logger.debug(f"New version draft created: {draft.id}")
        draft = current_rdm_records_service.update_draft(
            system_identity, draft.id, new_version_entry
        )

        if record.data.get("files", {}).get("enabled", False):
            current_rdm_records_service.import_files(system_identity, draft.id)
            logger.debug(f"Imported files from previous version: {draft.id}")

        self._sync_and_publish(draft, logger, existing_files, new_files)
        current_app.logger.info(f"New record version #{draft.id} published.")

    def _publish_edit(
        self, record_pid, update_metadata, should_update_files, existing_files, new_files, logger
    ):
        """Apply a metadata-only or metadata+file update to the current version."""
        logger.debug("Create draft for metadata update")
        draft = self.drafts.edit(record_pid)
        logger.debug(f"Draft created: {draft.id}")
        draft = current_rdm_records_service.update_draft(
            system_identity, draft.id, data=update_metadata
        )

        files = (existing_files, new_files) if should_update_files else None
        self._sync_and_publish(draft, logger, *files if files else (None, None))
        logger.info(f"Success: Record {record_pid} updated and published.")

    def _sync_and_publish(self, draft, logger, existing_files=None, new_files=None):
        """Sync files (when provided) then publish; deletes the draft on any failure."""
        try:
            if existing_files is not None:
                self.file_sync.sync(draft, existing_files, new_files, logger)
            self.drafts.publish(draft.id, logger)
        except Exception:
            try:
                current_rdm_records_service.delete_draft(system_identity, draft.id)
            except Exception:
                pass
            raise

    @hlog
    def _create_record(self, stream_entry, inspire_id=None, record_pid=None, logger=None):
        """Create and publish a new record draft for an incoming INSPIRE entry."""
        entry = stream_entry.entry

        doi = entry.get("pids", {}).get("doi", {})
        DATACITE_PREFIX = current_app.config["DATACITE_PREFIX"]
        if DATACITE_PREFIX in doi.get("identifier", ""):
            raise WriterError("Trying to create record with CDS DOI")

        file_entries = entry["files"].get("entries") or {}
        logger.debug(f"Files to create: {len(file_entries)}")
        logger.debug("Creating new record draft")

        draft = self.drafts.create(entry)
        logger.info(f"New draft is created ({draft.id}).")

        try:
            if file_entries:
                logger.info(
                    f"Creating new files. Filenames: {list(file_entries.keys())}."
                )
                self.file_sync.sync(draft, {}, file_entries, logger)
                logger.info("All the files successfully created.")

            self.drafts.add_community(draft)
        except Exception:
            current_rdm_records_service.delete_draft(system_identity, draft.id)
            logger.error(f"Draft {draft.id} is deleted due to errors.")
            raise

        # add_community succeeded — publish without file sync (files already uploaded above)
        self._sync_and_publish(draft, logger)
