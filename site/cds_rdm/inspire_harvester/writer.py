# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Writer module."""
import time
from io import BytesIO

import requests
from flask import current_app
from invenio_access.permissions import system_identity
from invenio_db import db
from invenio_rdm_records.proxies import current_rdm_records_service
from invenio_search.engine import dsl
from invenio_vocabularies.datastreams.errors import WriterError
from invenio_vocabularies.datastreams.writers import BaseWriter
from marshmallow import ValidationError


class InspireWriter(BaseWriter):
    """INSPIRE writer."""

    def _write_entry(self, entry, *args, **kwargs):
        """Write entry to CDS."""
        inspire_id = entry["id"]
        current_app.logger.debug(
            f"[inspire_id={inspire_id}] Starting _write_entry for INSPIRE record #{inspire_id}"
        )
        existing_records = self._get_existing_records(inspire_id)
        current_app.logger.debug(
            f"[inspire_id={inspire_id}] Found {existing_records.total} existing records for INSPIRE #{inspire_id}"
        )

        multiple_records_found = existing_records.total > 1
        should_update = existing_records.total == 1
        should_create = existing_records.total == 0

        existing_records_hits = existing_records.to_dict()["hits"]["hits"]
        existing_records_ids = [hit["id"] for hit in existing_records_hits]

        if multiple_records_found:
            current_app.logger.error(
                f"[inspire_id={inspire_id}] {existing_records.total} records found on CDS with the same INSPIRE ID ({inspire_id}). Found records ids: {', '.join(existing_records_ids)}."
            )
            return None
        elif should_update:
            current_app.logger.info(
                f"[inspire_id={inspire_id}] [recid={existing_records_ids[0]}] INSPIRE record #{inspire_id} has been matched to an existing record #{existing_records_ids[0]}."
            )
            self.update_record(
                entry, record_pid=existing_records_ids[0], inspire_id=inspire_id
            )
            current_app.logger.info(
                f"[inspire_id={inspire_id}] [recid={existing_records_ids[0]}] Record {existing_records_ids[0]} has been successfully updated from INSPIRE #{inspire_id}."
            )
            current_app.logger.debug(
                f"[inspire_id={inspire_id}] Completed _write_entry for INSPIRE record #{inspire_id}"
            )
            return "update"
        elif should_create:
            # no existing record in CDS - create and publish a new one
            current_app.logger.debug(
                f"[inspire_id={inspire_id}] Creating new record for INSPIRE #{inspire_id}"
            )
            self._create_new_record(entry)
            current_app.logger.debug(
                f"[inspire_id={inspire_id}] Completed _write_entry for INSPIRE record #{inspire_id}"
            )
            return "create"
        else:
            current_app.logger.error(
                f"[inspire_id={inspire_id}] Unexpected condition in decision logic"
            )
            raise NotImplemented()

    def _process_entry(self, stream_entry, *args, **kwargs):
        """Helper method to process a single entry."""
        entry = stream_entry.entry
        inspire_id = entry["id"]
        current_app.logger.debug(f"[inspire_id={inspire_id}] Starting _process_entry")
        op_type = None
        try:
            op_type = self._write_entry(entry, *args, **kwargs)
        except WriterError as e:
            error_message = f"[inspire_id={entry['id']}] Error while processing entry {entry['id']}: {str(e)}."
            current_app.logger.error(error_message)
            stream_entry.errors.append(error_message)
        except ValidationError as e:
            error_message = f"[inspire_id={entry['id']}] Validation error while processing entry {entry['id']}: {str(e)}."
            current_app.logger.error(error_message)
            stream_entry.errors.append(error_message)
        except Exception as e:
            error_message = f"[inspire_id={entry['id']}] Unexpected error while processing entry {entry['id']}: {str(e)}."
            current_app.logger.error(error_message)
            stream_entry.errors.append(error_message)
        stream_entry.op_type = op_type
        current_app.logger.debug(f"[inspire_id={inspire_id}] Completed _process_entry")
        return stream_entry

    def write(self, stream_entry, *args, **kwargs):
        """Creates or updates the record in CDS."""
        return self._process_entry(stream_entry, *args, **kwargs)

    def write_many(self, stream_entries, *args, **kwargs):
        """Creates or updates the records in CDS."""
        current_app.logger.debug(
            f"Starting write_many with {len(stream_entries)} entries"
        )
        for i, stream_entry in enumerate(stream_entries, 1):
            current_app.logger.debug(f"Processing entry {i}/{len(stream_entries)}")
            self._process_entry(stream_entry, *args, **kwargs)
        current_app.logger.info(f"All entries processed.")
        current_app.logger.debug(f"Completed write_many processing")
        return stream_entries

    def _get_existing_records(self, inspire_id):
        """Find records that have already been harvested from INSPIRE."""
        current_app.logger.debug(
            f"[inspire_id={inspire_id}] Searching for existing records with INSPIRE ID {inspire_id}"
        )
        # for now checking only by inspire id
        filters = [
            dsl.Q("term", **{"metadata.identifiers.scheme": "inspire"}),
            dsl.Q("term", **{"metadata.identifiers.identifier": inspire_id}),
        ]
        combined_filter = dsl.Q("bool", filter=filters)
        current_app.logger.debug(f"[inspire_id={inspire_id}] Search filters: {filters}")

        result = current_rdm_records_service.search(
            system_identity, extra_filter=combined_filter
        )
        current_app.logger.debug(
            f"[inspire_id={inspire_id}] Search completed, found {result.total} records"
        )
        return result

    def update_record(self, entry, record_pid, inspire_id):
        """Update existing record."""
        current_app.logger.debug(
            f"[inspire_id={inspire_id}] [recid={record_pid}] Starting update_record"
        )

        current_app.logger.debug(
            f"[inspire_id={inspire_id}] [recid={record_pid}] Reading existing record"
        )
        record = current_rdm_records_service.read(system_identity, record_pid)
        record_dict = record.to_dict()
        existing_files = record_dict["files"]["entries"]
        new_files = entry["files"].get("entries", {})

        current_app.logger.debug(
            f"[inspire_id={inspire_id}] [recid={record_pid}] Existing files count: {len(existing_files)}, New files count: {len(new_files)}"
        )

        # Normalize the checksum format in existing for comparison
        existing_checksums = [
            value["checksum"] for key, value in existing_files.items()
        ]

        current_app.logger.debug(
            f"[inspire_id={inspire_id}] [recid={record_pid}] Existing files' checksums: {existing_checksums}."
        )
        new_checksums = [value["checksum"] for key, value in new_files.items()]
        current_app.logger.debug(
            f"[inspire_id={inspire_id}] [recid={record_pid}] New files' checksums: {new_checksums}."
        )

        should_create_new_version = existing_checksums != new_checksums
        current_app.logger.debug(
            f"[inspire_id={inspire_id}] [recid={record_pid}] Should create new version: {should_create_new_version}"
        )

        if should_create_new_version:
            current_app.logger.debug(
                f"[inspire_id={inspire_id}] [recid={record_pid}] File differences detected, creating new version"
            )
            self._create_new_version(entry, record, inspire_id)
        else:
            current_app.logger.info(
                f"[inspire_id={inspire_id}] [recid={record_dict['id']}] No file changes between CDS #{record_dict['id']} and INSPIRE #{inspire_id}. Updating metadata."
            )
            current_app.logger.debug(
                f"[inspire_id={inspire_id}] [recid={record_dict['id']}] Creating draft for metadata update"
            )
            draft = current_rdm_records_service.edit(system_identity, record_pid)
            current_app.logger.debug(
                f"[inspire_id={inspire_id}] [recid={record_dict['id']}] Draft created with ID: {draft.id}"
            )

            # TODO make this indempotent
            current_app.logger.debug(
                f"[inspire_id={inspire_id}] [recid={record_dict['id']}] Updating draft with new metadata"
            )
            current_rdm_records_service.update_draft(
                system_identity, draft.id, data=entry
            )
            current_app.logger.info(
                f"[inspire_id={inspire_id}] [recid={record_dict['id']}] Draft {draft.id} is updated. Publishing it."
            )

            try:
                current_app.logger.debug(
                    f"[inspire_id={inspire_id}] [recid={record_dict['id']}] Publishing draft {draft.id}"
                )
                current_rdm_records_service.publish(system_identity, draft.id)
                current_app.logger.info(
                    f"[inspire_id={inspire_id}] [recid={record_dict['id']}] Record {record_dict['id']} is successfully updated and published."
                )
            except ValidationError as e:
                current_app.logger.error(
                    f"[inspire_id={inspire_id}] [recid={record_dict['id']}] Draft {record_dict['id']} failed publishing because of validation errors: {e}."
                )
                current_rdm_records_service.delete_draft(system_identity, draft["id"])
                raise e
            except Exception as e:
                current_rdm_records_service.delete_draft(system_identity, draft["id"])
                raise WriterError(
                    f"Draft {draft.id} failed publishing because of an unexpected error: {str(e)}."
                )

    def _create_new_version(self, entry, record, inspire_id):
        """For records with updated files coming from INSPIRE, create and publish a new version."""
        current_app.logger.debug(
            f"[inspire_id={inspire_id}] [recid={record.id}] Starting _create_new_version"
        )

        current_app.logger.debug(
            f"[inspire_id={inspire_id}] [recid={record.id}] Creating new version draft"
        )
        new_version_draft = current_rdm_records_service.new_version(
            system_identity, record.id
        )
        current_app.logger.debug(
            f"[inspire_id={inspire_id}] [recid={record.id}] New version draft created with ID: {new_version_draft.id}"
        )

        current_app.logger.info(
            f"[inspire_id={inspire_id}] [recid={record.id}] Differences between existing and new files checksums were found. Draft of a new version of the record "
            f"is created. Draft ID: {new_version_draft.id}."
        )
        record_dict = record.to_dict()
        existing_files = record_dict["files"]["entries"]
        new_files = entry["files"].get("entries", {})

        existing_checksums = [
            value["checksum"] for key, value in existing_files.items()
        ]
        new_checksums = [value["checksum"] for key, value in new_files.items()]

        files_to_create = list(set(new_checksums) - set(existing_checksums))
        files_to_delete = list(set(existing_checksums) - set(new_checksums))

        current_app.logger.info(
            f"[inspire_id={inspire_id}] [recid={record.id}] New checksums: {files_to_create}."
        )
        current_app.logger.info(
            f"[inspire_id={inspire_id}] [recid={record.id}] Checksums to delete {files_to_delete}."
        )

        current_app.logger.debug(
            f"[inspire_id={inspire_id}] [recid={record.id}] Importing files to new version draft"
        )
        current_rdm_records_service.import_files(system_identity, new_version_draft.id)

        current_app.logger.debug(
            f"[inspire_id={inspire_id}] [recid={record.id}] Deleting outdated files"
        )
        for filename, file_data in existing_files.items():
            if file_data["checksum"] in files_to_delete:
                current_app.logger.debug(
                    f"[inspire_id={inspire_id}] [recid={record.id}] Deleting file: {filename}"
                )
                current_rdm_records_service.draft_files.delete_file(
                    system_identity, new_version_draft.id, filename
                )

        current_app.logger.info(
            f"[inspire_id={inspire_id}] [recid={record.id}] {len(existing_files.items())} files have been successfully deleted."
        )

        current_app.logger.debug(
            f"[inspire_id={inspire_id}] [recid={record.id}] Creating new files"
        )
        for key, file in new_files.items():
            if file["checksum"] in files_to_create:
                current_app.logger.debug(
                    f"[inspire_id={inspire_id}] [recid={record.id}] Processing new file: {key}"
                )
                inspire_url = file.pop("inspire_url")
                file_content = self._fetch_file(inspire_url)
                if not file_content:
                    current_app.logger.warning(
                        f"[inspire_id={inspire_id}] [recid={record.id}] Failed to fetch file content for: {key}"
                    )
                    return
                self._create_file(file, file_content, new_version_draft, inspire_id)
        current_app.logger.info(
            f"[inspire_id={inspire_id}] [recid={record.id}] {len(new_files.items())} files have been successfully created."
        )

        # update metadata TODO make indempotent
        current_app.logger.debug(
            f"[inspire_id={inspire_id}] [recid={record.id}] Updating metadata for new version draft"
        )
        current_rdm_records_service.update_draft(
            system_identity, new_version_draft.id, entry
        )

        try:
            current_app.logger.debug(
                f"[inspire_id={inspire_id}] [recid={record.id}] Publishing new version draft"
            )
            current_rdm_records_service.publish(system_identity, new_version_draft.id)
            current_app.logger.info(
                f"[inspire_id={inspire_id}] [recid={new_version_draft.id}] Metadata is successfully updated and record #{new_version_draft.id} is published."
            )
        except ValidationError as e:
            current_rdm_records_service.delete_draft(
                system_identity, new_version_draft.id
            )
            raise WriterError(
                f"Draft {new_version_draft.id} failed publishing because of validation errors: {e}."
            )
        except Exception as e:
            current_rdm_records_service.delete_draft(
                system_identity, new_version_draft.id
            )
            raise WriterError(
                f"Draft {new_version_draft.id} failed publishing because of an unexpected error: {str(e)}."
            )

    def _add_community(self, draft):
        """Add CERN Scientific Community to the draft."""
        with db.session.begin_nested():
            community_id = current_app.config["CDS_CERN_SCIENTIFIC_COMMUNITY_ID"]
            draft_obj = current_rdm_records_service.draft_cls.pid.resolve(
                draft.id, registered_only=False
            )
            draft_obj.parent.communities.add(
                community_id,
            )
            draft_obj.parent.communities.default = community_id
            draft_obj.parent.commit()

    def _create_new_record(self, entry):
        """For new records coming from INSPIRE, create and publish a draft in CDS."""
        inspire_id = entry["id"]
        current_app.logger.debug(
            f"[inspire_id={inspire_id}] Starting _create_new_record"
        )

        file_entries = entry["files"].get("entries", None)
        current_app.logger.debug(
            f"[inspire_id={inspire_id}] Files to create: {len(file_entries) if file_entries else 0}"
        )

        current_app.logger.debug(f"[inspire_id={inspire_id}] Creating new record draft")
        draft = current_rdm_records_service.create(system_identity, data=entry)
        current_app.logger.info(
            f"[inspire_id={inspire_id}] [recid={draft.id}] New draft is created ({draft.id})."
        )
        try:
            current_app.logger.info(
                f"[inspire_id={inspire_id}] [recid={draft.id}] Creating new files for the draft. Filenames: {list(file_entries.keys())}."
            )
            for key, file_data in file_entries.items():
                current_app.logger.debug(
                    f"[inspire_id={inspire_id}] [recid={draft.id}] Processing file: {key}"
                )
                inspire_url = file_data.pop("inspire_url")
                file_content = self._fetch_file(inspire_url)
                if not file_content:
                    current_app.logger.warning(
                        f"[inspire_id={inspire_id}] [recid={draft.id}] Failed to fetch file content for: {key}"
                    )
                    return
                self._create_file(file_data, file_content, draft, inspire_id)
            current_app.logger.info(
                f"[inspire_id={inspire_id}] [recid={draft.id}] All the files have been successfully created."
            )

        except Exception as e:
            current_rdm_records_service.delete_draft(system_identity, draft["id"])
            current_app.logger.info(
                f"[inspire_id={inspire_id}] [recid={draft['id']}] Draft is deleted successfully."
            )
            raise WriterError(
                f"Draft {draft.id} failed creating because of an unexpected error: {str(e)}."
            )
        else:
            try:
                current_app.logger.debug(
                    f"[inspire_id={inspire_id}] [recid={draft['id']}] Adding community to draft"
                )
                self._add_community(draft)
                current_app.logger.debug(
                    f"[inspire_id={inspire_id}] [recid={draft['id']}] Publishing draft"
                )
                current_rdm_records_service.publish(system_identity, draft["id"])
                current_app.logger.info(
                    f"[inspire_id={inspire_id}] [recid={draft['id']}] Draft {draft['id']} has been published successfully."
                )
            except ValidationError as e:
                current_rdm_records_service.delete_draft(system_identity, draft["id"])
                raise WriterError(
                    f"Draft {draft['id']} failed publishing because of validation errors: {e}."
                )
            except Exception as e:
                current_rdm_records_service.delete_draft(system_identity, draft["id"])
                raise WriterError(
                    f"Draft {draft.id} failed publishing because of an unexpected error: {str(e)}."
                )

    def _fetch_file(self, inspire_url, max_retries=3):
        """Fetch file content from inspire url."""
        current_app.logger.debug(f"Starting file fetch from URL: {inspire_url}")
        attempt = 0
        while attempt < max_retries:
            attempt += 1
            try:
                current_app.logger.debug(
                    f"Attempt {attempt}/{max_retries} - HEAD request to: {inspire_url}"
                )
                head = requests.head(inspire_url, allow_redirects=True)
                url = head.url
                current_app.logger.info(
                    f"Sending request to retrieve file. URL: {url}."
                )
                current_app.logger.debug(f"GET request to: {url}")
                response = requests.get(url, stream=True)
                current_app.logger.debug(
                    f"Response status code: {response.status_code}"
                )
                if response.status_code == 200:
                    # TODO improve when it makes sense to upload multipart?
                    current_app.logger.debug("File retrieved successfully.")
                    return BytesIO(response.content)
                else:
                    current_app.logger.warning(
                        f"Retrieving file request failed. "
                        f"Attempt {attempt}/{max_retries} "
                        f"Error {response.status_code}."
                        f" URL: {url}."
                    )
            except Exception as e:
                current_app.logger.warning(
                    f"Attempt {attempt}/{max_retries} failed with exception: {e}"
                )
                current_app.logger.debug("Retrying in 1 minute...")
                time.sleep(60)

        current_app.logger.error(
            f"Retrieving file request failed. Max retries {max_retries} reached."
            f" URL: {inspire_url}."
        )

    def _create_file(self, file_data, file_content, draft, inspire_id):
        """Create a new file."""
        current_app.logger.debug(
            f"[inspire_id={inspire_id}] [recid={draft.id}] Start creation of a new file. Filename: '{file_data['key']}'."
        )
        service = current_rdm_records_service
        try:
            service.draft_files.init_files(
                system_identity,
                draft.id,
                [file_data],
            )
            current_app.logger.debug(
                f"[inspire_id={inspire_id}] [recid={draft.id}] Init files finished successfully. Filename: '{file_data['key']}'."
            )
            service.draft_files.set_file_content(
                system_identity,
                draft.id,
                file_data["key"],
                file_content,
            )
            current_app.logger.debug(
                f"[inspire_id={inspire_id}] [recid={draft.id}] Set file content finished successfully. Filename: '{file_data['key']}'."
            )
            result = service.draft_files.commit_file(
                system_identity, draft.id, file_data["key"]
            )

            current_app.logger.debug(
                f"[inspire_id={inspire_id}] [recid={draft.id}] Commit file finished successfully. Filename: '{file_data['key']}'."
            )
            inspire_checksum = file_data["checksum"]
            new_checksum = result.to_dict()["checksum"]
            assert inspire_checksum == new_checksum
        except AssertionError as e:
            ## TODO draft? delete record completely?
            current_app.logger.error(
                f"[inspire_id={inspire_id}] [recid={draft.id}] Files checksums don't match. Deleting created file from the draft. Filename: '{file_data['key']}'."
            )
            service.draft_files.delete_file(system_identity, draft.id, file_data["key"])
            current_app.logger.debug(
                f"[inspire_id={inspire_id}] [recid={draft.id}] File is deleted successfully. Filename: '{file_data['key']}'."
            )
            raise WriterError(
                f"File {file_data['key']} checksum mismatch. Expected: {inspire_checksum}, got: {new_checksum}."
            )
        except Exception as e:
            current_app.logger.error(
                f"[inspire_id={inspire_id}] [recid={draft.id}] An error occurred while creating a file. Deleting the created file. Filename: '{file_data['key']}'. Error: {e}."
            )
            service.draft_files.delete_file(system_identity, draft.id, file_data["key"])
            current_app.logger.info(
                f"[inspire_id={inspire_id}] [recid={draft.id}] File is deleted successfully. Filename: '{file_data['key']}'."
            )
            raise WriterError(
                f"File {file_data['key']} creation failed because of an unexpected error: {str(e)}."
            )
