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
from invenio_rdm_records.proxies import current_rdm_records_service
from invenio_vocabularies.datastreams.errors import WriterError
from invenio_vocabularies.datastreams.writers import BaseWriter
from marshmallow import ValidationError

from cds_rdm.inspire_harvester.load.draft import DraftLifecycleManager
from cds_rdm.inspire_harvester.load.files import FileSynchronizer
from cds_rdm.inspire_harvester.load.matcher import RecordMatcher
from cds_rdm.inspire_harvester.logger import Logger, hlog
from cds_rdm.inspire_harvester.update.config import UPDATE_STRATEGY_CONFIG
from cds_rdm.inspire_harvester.update.engine import UpdateContext, UpdateEngine
from cds_rdm.inspire_harvester.utils import compare_metadata


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
            import traceback
            traceback.print_exc()
        except ValidationError as e:
            error_message = f"Validation error while processing entry: {str(e)}."
            import traceback
            traceback.print_exc()
        except Exception as e:
            import traceback
            traceback.print_exc()

        if error_message:
            logger.error(error_message)
            stream_entry.errors.append(f"[inspire_id={inspire_id}] {error_message}")

        stream_entry.op_type = op_type
        return stream_entry

    @hlog
    def _route(self, stream_entry, inspire_id=None, record_pid=None, logger=None):
        """Route the entry to create or update based on existing record lookup."""
        match_result = self.matcher.match(stream_entry, inspire_id, logger)
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
    def _update_record(
        self, stream_entry, record_pid=None, inspire_id=None, logger=None
    ):
        """Dispatch to in-place edit or new-version based on file/DOI state."""
        entry = {k: v for k, v in stream_entry.entry.items() if k != "_inspire_ctx"}
        ctx = stream_entry.entry["_inspire_ctx"]
        record = current_rdm_records_service.read(system_identity, record_pid)
        record_dict = record.to_dict()

        should_update_files = self.file_sync.check_files_should_update(
            record, entry, logger
        )
        # Enable files on the entry *before* the engine sees it so update_metadata carries it
        if should_update_files and not record_dict.get("files", {}).get(
            "enabled", False
        ):
            entry["files"]["enabled"] = True

        has_cds_doi = record.data["pids"].get("doi", {}).get("provider") == "datacite"

        latest_res_type_changed = (
            record.data["metadata"]["resource_type"]["id"]
            != entry["metadata"]["resource_type"]["id"]
        )

        if should_update_files and has_cds_doi and latest_res_type_changed:
            engine = UpdateEngine(
                strategies=UPDATE_STRATEGY_CONFIG, fail_on_conflict=False
            )
            result = engine.update(
                record_dict, entry, UpdateContext(source="inspire_import"), logger
            )
            update_metadata = result.updated

            self._resource_type_versioning(record, update_metadata, ctx, logger)
        else:
            engine = UpdateEngine(
                strategies=UPDATE_STRATEGY_CONFIG, fail_on_conflict=True
            )
            result = engine.update(
                record_dict, entry, UpdateContext(source="inspire_import"), logger
            )
            update_metadata = result.updated
            is_pids_equal = update_metadata["pids"] == record_dict["pids"]
            is_metadata_equal = compare_metadata(
                update_metadata["metadata"], record_dict["metadata"]
            )
            is_custom_fields_equal = compare_metadata(
                update_metadata["custom_fields"], record_dict["custom_fields"]
            )

            if (
                is_pids_equal
                and is_metadata_equal
                and is_custom_fields_equal
                and not should_update_files
            ):
                logger.info(f"Skipping record, already up to date")
            else:
                self._publish_edit(
                    record_pid,
                    update_metadata,
                    logger,
                )

    def _resource_type_versioning(self, record, update_metadata, ctx, logger):

        search_result = current_rdm_records_service.scan_versions(
            identity=system_identity,
            id_=record.id,
        )
        existing_record_versions = {
            hit["metadata"]["resource_type"]["id"]: hit["id"] for hit in search_result
        }
        logger.debug(
            f"Resource types mapped to versions {existing_record_versions.keys()}"
        )
        for version in ctx["versions"]:
            # find if version with this resource type exists
            incoming_resource_type = version["metadata"]["resource_type"]["id"]
            logger.info(f"Processing {incoming_resource_type} version")
            if incoming_resource_type in existing_record_versions:
                version_record = current_rdm_records_service.read(
                    system_identity, existing_record_versions[incoming_resource_type]
                )
                should_update_files = self.file_sync.check_files_should_update(
                    version_record, version, logger
                )
                if should_update_files:
                    self._publish_new_version(version_record, version, logger)
                    logger.info(
                        f"Created new version for resource type {incoming_resource_type}"
                    )
                else:
                    self._publish_edit(version_record.id, version, logger)
                    logger.info(
                        f"Edited {version_record.id} for resource type {incoming_resource_type}"
                    )
            else:
                self._publish_new_version(record, version, logger)

        latest_record_version = current_rdm_records_service.record_cls.get_latest_published_by_parent(
            record._record.parent
        )
        record = current_rdm_records_service.read(system_identity, latest_record_version["id"])
        # publish the latest version at the end
        self._publish_new_version(record, update_metadata, logger)
        logger.info(
            f"Created new version {update_metadata['metadata']['resource_type']}"
        )

    def _publish_new_version(self, record, update_metadata, logger):
        """Create and publish a new version with updated metadata and synced files."""
        draft = self.drafts.new_version(record["id"])

        new_version_entry = deepcopy(update_metadata)

        if "pids" in new_version_entry:
            del new_version_entry["pids"]["oai"]
            if new_version_entry["pids"]["doi"]["provider"] != "external":
                del new_version_entry["pids"]["doi"]

        logger.debug(f"New version draft created: {draft.id}")
        draft = self.drafts.update(draft, new_version_entry)
        self.file_sync.sync(draft, record, update_metadata, logger)
        self.drafts.publish(draft.id, logger)
        current_app.logger.info(f"New record version #{draft.id} published.")

    def _publish_edit(
        self,
        record_pid,
        update_metadata,
        logger,
    ):
        """Apply a metadata-only or metadata+file update to the current version."""
        logger.debug("Create draft for metadata update")
        draft = self.drafts.edit(record_pid)
        logger.debug(f"Draft created: {draft.id}")
        draft = self.drafts.update(draft, update_metadata)
        self.file_sync.sync(draft, draft, update_metadata, logger, import_files=False)
        self.drafts.publish(draft.id, logger)
        logger.info(f"Success: Record {record_pid} updated and published.")

    @hlog
    def _create_record(
        self, stream_entry, inspire_id=None, record_pid=None, logger=None
    ):
        """Create and publish a new record draft for an incoming INSPIRE entry."""
        entry = {k: v for k, v in stream_entry.entry.items() if k != "_inspire_ctx"}
        ctx = stream_entry.entry["_inspire_ctx"]
        doi = entry.get("pids", {}).get("doi", {})
        DATACITE_PREFIX = current_app.config["DATACITE_PREFIX"]
        if DATACITE_PREFIX in doi.get("identifier", ""):
            raise WriterError(
                "Trying to create record with CDS DOI "
                "- record should be updated instead."
            )

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
                self.file_sync.sync(draft, {}, entry, logger)
                logger.info("All the files successfully created.")

            self.drafts.add_community(draft)
        except Exception:
            current_rdm_records_service.delete_draft(system_identity, draft.id)
            logger.error(f"Draft {draft.id} is deleted due to errors.")
            raise

        # add_community succeeded — publish without file sync (files already uploaded above)
        self.drafts.publish(draft.id, logger)
