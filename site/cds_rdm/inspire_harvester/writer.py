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
from invenio_rdm_records.proxies import current_rdm_records_service
from invenio_search.engine import dsl
from invenio_vocabularies.datastreams.errors import WriterError
from invenio_vocabularies.datastreams.writers import BaseWriter


class InspireWriter(BaseWriter):
    """INSPIRE writer."""

    def _write_entry(self, entry, *args, **kwargs):
        """Write entry to CDS."""
        current_app.logger.info("Start writing entry.")
        inspire_id = entry["id"]
        existing_records = self._get_existing_records(inspire_id)
        multiple_records_found = existing_records.total > 1
        should_update = existing_records.total == 1
        should_create = existing_records.total == 0

        existing_records_hits = existing_records.to_dict()["hits"]["hits"]
        existing_records_ids = [hit["id"] for hit in existing_records_hits]
        current_app.logger.debug(
            f"IDs of existing records found: {existing_records_ids}."
        )

        if multiple_records_found:
            current_app.logger.error(
                f"{existing_records.total} records found on CDS with the same INSPIRE ID ({inspire_id})."
            )
            raise WriterError(
                f"More than 1 record found with INSPIRE id {inspire_id}. CDS records found: {', '.join(existing_records_ids)}"
            )
        elif should_update:
            self.update_record(entry, record_pid=existing_records_ids[0])
            current_app.logger.info("Record has been successfully updated.")
        elif should_create:
            # no existing record in CDS - create and publish a new one
            self._create_new_record(entry)
            current_app.logger.info("New record has been successfully created.")
        else:
            raise NotImplemented()

    def write(self, stream_entry, *args, **kwargs):
        """Creates or updates the record in CDS."""
        entry = stream_entry.entry
        current_app.logger.info(
            f"Writer entry point. Start processing stream entry: {entry}."
        )
        self._write_entry(entry, *args, **kwargs)
        current_app.logger.info(f"Writing entry finished.")
        return stream_entry

    def write_many(self, stream_entries, *args, **kwargs):
        """Creates or updates the record in CDS."""
        entries = [entry.entry for entry in stream_entries]
        current_app.logger.info(
            f"Writer entry point. Start processing a batch of stream entries: {entries}."
        )
        for entry in entries:
            self._write_entry(entry, *args, *kwargs)
        current_app.logger.info(f"Writing entries finished.")
        return stream_entries

    def _get_existing_records(self, inspire_id):
        """Find records that have already been harvested from INSPIRE."""
        current_app.logger.info(
            f"Start retrieving existing records by INSPIRE ID ({inspire_id})."
        )
        # for now checking only by inspire id
        filters = [
            dsl.Q("term", **{"metadata.identifiers.scheme": "inspire"}),
            dsl.Q("term", **{"metadata.identifiers.identifier": inspire_id}),
        ]
        combined_filter = dsl.Q("bool", filter=filters)
        current_app.logger.debug(
            f"Filter for searching for existing records: {combined_filter}."
        )
        return current_rdm_records_service.search(
            system_identity, extra_filter=combined_filter
        )

    def update_record(self, entry, record_pid):
        """Update existing record."""
        current_app.logger.info(
            f"Start updating an existing record on CDS. Recid: {record_pid}."
        )
        record = current_rdm_records_service.read(system_identity, record_pid)
        record_dict = record.to_dict()
        current_app.logger.debug(f"Existing record details: {record_dict}.")
        existing_files = record_dict["files"]["entries"]
        current_app.logger.debug(f"Existing record's files details: {existing_files}.")
        new_files = entry["files"].get("entries", {})

        if not new_files:
            current_app.logger.error(
                f"INSPIRE record #{entry['id']} has no files. Metadata-only records are not supported. Aborting record writer."
            )
            return

        # Normalize the checksum format in existing for comparison
        existing_checksums = [
            value["checksum"] for key, value in existing_files.items()
        ]

        current_app.logger.debug(f"Existing files' checksums: {existing_checksums}.")
        new_checksums = [value["checksum"] for key, value in new_files.items()]
        current_app.logger.debug(f"New files' checksums: {new_checksums}.")

        should_create_new_version = existing_checksums != new_checksums

        if should_create_new_version:
            current_app.logger.info(
                "Differences between existing and new files checksums were found. Creating a new version for the record."
            )
            self._create_new_version(entry, record)
        else:
            current_app.logger.info(
                "Files in the existing record and the record from INSPIRE are the same. No need for creating a new version. Only metadata update is needed."
            )
            draft = current_rdm_records_service.edit(system_identity, record_pid)
            # TODO make this indempotent
            current_app.logger.info(
                f"New draft is created ({draft.id}). Updating it with new info: {entry}."
            )
            current_rdm_records_service.update_draft(
                system_identity, draft.id, data=entry
            )
            current_app.logger.info("Draft is updated. Publishing it.")
            current_rdm_records_service.publish(system_identity, draft.id)
            current_app.logger.info("New draft is successfully published.")

    def _create_new_version(self, entry, record):
        """For records with updated files coming from INSPIRE, create and publish a new version."""
        current_app.logger.info("Start creating a new version.")
        new_version_draft = current_rdm_records_service.new_version(
            system_identity, record.id
        )

        current_app.logger.info(
            f"New version draft is created. ID: {new_version_draft.id}."
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
            f"Details of the files to be added to the record: {files_to_create}."
        )
        current_app.logger.info(
            f"Details of the files to be deleted from the record: {files_to_delete}."
        )

        current_rdm_records_service.import_files(system_identity, new_version_draft.id)

        for filename, file_data in existing_files.items():
            if file_data["checksum"] in files_to_delete:
                current_rdm_records_service.draft_files.delete_file(
                    system_identity, new_version_draft.id, filename
                )
        current_app.logger.info("Files have been successfully deleted.")

        for key, file in new_files.items():
            if file["checksum"] in files_to_create:
                inspire_url = file.pop("inspire_url")
                file_content = self._fetch_file(inspire_url)
                if not file_content:
                    return
                self._create_file(file, file_content, new_version_draft)
        current_app.logger.info("Files have been successfully created.")

        # update metadata TODO make indempotent
        current_app.logger.info("Start updating metadata.")
        current_rdm_records_service.update_draft(
            system_identity, new_version_draft.id, entry
        )
        current_rdm_records_service.publish(system_identity, new_version_draft.id)
        current_app.logger.info(
            "Metadata is successfully updated and record is published."
        )

    def _create_new_record(self, entry):
        """For new records coming from INSPIRE, create and publish a draft in CDS."""
        current_app.logger.info("Start creating a new record.")
        file_entries = entry["files"].get("entries", None)
        if not file_entries:
            current_app.logger.error(
                f"INSPIRE record #{entry['id']} has no files. Metadata-only records are not supported. Aborting record writer."
            )
            return

        draft = current_rdm_records_service.create(system_identity, data=entry)
        current_app.logger.info(f"New draft is created ({draft.id}).")
        try:
            current_app.logger.info(
                f"Creating new files for the draft: {file_entries}."
            )
            for key, file_data in file_entries.items():
                inspire_url = file_data.pop("inspire_url")
                file_content = self._fetch_file(inspire_url)
                if not file_content:
                    return
                self._create_file(file_data, file_content, draft)
            current_app.logger.info(f"All the files have been successfully created.")

        except WriterError as e:
            current_app.logger.error(
                f"An error occurred while creating files. Deleting the created draft. Error: {e}."
            )
            current_rdm_records_service.delete_draft(system_identity, draft["id"])
            current_app.logger.error("Draft is deleted successfully.")
            raise e
        else:
            current_rdm_records_service.publish(system_identity, draft["id"])
            current_app.logger.error("Draft has been published successfully.")

    def _fetch_file(self, inspire_url, max_retries=3):
        """Fetch file content from inspire url."""
        attempt = 0
        while attempt < max_retries:
            attempt += 1
            try:
                head = requests.head(inspire_url, allow_redirects=True)
                url = head.url
                current_app.logger.info(
                    f"Sending request to retrieve file. URL: {url}."
                )
                response = requests.get(url, stream=True)
                if response.status_code == 200:
                    # TODO improve when it makes sense to upload multipart?
                    current_app.logger.info("File retrieved successfully.")
                    return BytesIO(response.content)
                else:
                    current_app.logger.error(
                        f"Retrieving file request failed. "
                        f"Attempt {attempt}/{max_retries} "
                        f"Error {response.status_code}."
                        f" URL: {url}."
                    )
            except Exception as e:
                current_app.logger.error("Retrying in 1 minute...")
                time.sleep(60)

        current_app.logger.error(
            f"Retrieving file request failed. Max retries {max_retries} reached."
            f" URL: {inspire_url}."
        )

    def _create_file(self, file_data, file_content, draft):
        """Create a new file."""
        current_app.logger.info("Start creation of a new file.")
        service = current_rdm_records_service
        try:
            service.draft_files.init_files(
                system_identity,
                draft.id,
                [file_data],
            )
            current_app.logger.info("Init files finished successfully.")
            service.draft_files.set_file_content(
                system_identity,
                draft.id,
                file_data["key"],
                file_content,
            )
            current_app.logger.info("Set file content finished successfully.")
            result = service.draft_files.commit_file(
                system_identity, draft.id, file_data["key"]
            )

            current_app.logger.info("Commit file finished successfully.")
            inspire_checksum = file_data["checksum"]
            new_checksum = result.to_dict()["checksum"]
            assert inspire_checksum == new_checksum
        except AssertionError as e:
            ## TODO draft? delete record completely?
            current_app.logger.info(
                "Files checksums don't match. Deleting created file from the draft."
            )
            service.draft_files.delete_file(system_identity, draft.id, file_data["key"])
            current_app.logger.info("File is deleted successfully.")
            raise e
