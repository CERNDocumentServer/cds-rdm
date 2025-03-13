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
        inspire_id = entry["id"]
        existing_records = self._get_existing_records(inspire_id)
        multiple_records_found = existing_records.total > 1
        should_update = existing_records.total == 1
        should_create = existing_records.total == 0

        existing_records_hits = existing_records.to_dict()["hits"]["hits"]
        existing_records_ids = [hit["id"] for hit in existing_records_hits]

        if multiple_records_found:
            raise WriterError(
                f"More than 1 record found with INSPIRE id {inspire_id}. CDS records found: {', '.join(existing_records_ids)}"
            )
        elif should_update:
            self.update_record(entry, record_pid=existing_records_ids[0])
        elif should_create:
            # no existing record in CDS - create and publish a new one
            self._create_new_record(entry)
        else:
            raise NotImplemented()

    def write(self, stream_entry, *args, **kwargs):
        """Creates or updates the record in CDS."""
        entry = stream_entry.entry
        self._write_entry(entry, *args, **kwargs)
        return stream_entry

    def write_many(self, stream_entries, *args, **kwargs):
        """Creates or updates the record in CDS."""
        entries = [entry.entry for entry in stream_entries]

        for entry in entries:
            self._write_entry(entry, *args, *kwargs)
        return stream_entries

    def _get_existing_records(self, inspire_id):
        """Find records that have already been harvested from INSPIRE."""
        # for now checking only by inspire id
        filters = [
            dsl.Q("term", **{"metadata.identifiers.scheme": "inspire"}),
            dsl.Q("term", **{"metadata.identifiers.identifier": inspire_id}),
        ]
        combined_filter = dsl.Q("bool", filter=filters)
        return current_rdm_records_service.search(
            system_identity, extra_filter=combined_filter
        )

    def update_record(self, entry, record_pid):
        """Update existing record."""
        record = current_rdm_records_service.read(system_identity, record_pid)
        record_dict = record.to_dict()

        existing_files = record_dict["files"]["entries"]
        new_files = entry["files"].get("entries", {})

        if not new_files:
            # TODO log the absence of files
            return
            # raise WriterError(f"INSPIRE record #{entry['id']} has no files. Aborting.")

        # Normalize the checksum format in existing for comparison
        existing_checksums = [
            value["checksum"] for key, value in existing_files.items()
        ]
        new_checksums = [value["checksum"] for key, value in new_files.items()]

        should_create_new_version = existing_checksums != new_checksums

        if should_create_new_version:
            self._create_new_version(entry, record)
        else:
            draft = current_rdm_records_service.edit(system_identity, record_pid)
            # TODO make this indempotent
            current_rdm_records_service.update_draft(
                system_identity, draft.id, data=entry
            )
            current_rdm_records_service.publish(system_identity, draft.id)

    def _create_new_version(self, entry, record):
        """For records with updated files coming from INSPIRE, create and publish a new version."""
        new_version_draft = current_rdm_records_service.new_version(
            system_identity, record.id
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

        current_rdm_records_service.import_files(system_identity, new_version_draft.id)

        for filename, file_data in existing_files.items():
            if file_data["checksum"] in files_to_delete:
                current_rdm_records_service.draft_files.delete_file(
                    system_identity, new_version_draft.id, filename
                )

        for key, file in new_files.items():
            if file["checksum"] in files_to_create:
                inspire_url = file.pop("inspire_url")
                file_content = self._fetch_file(inspire_url)
                if not file_content:
                    return
                self._create_file(file, file_content, new_version_draft)
        # update metadata TODO make indempotent
        current_rdm_records_service.update_draft(
            system_identity, new_version_draft.id, entry
        )
        current_rdm_records_service.publish(system_identity, new_version_draft.id)

    def _create_new_record(self, entry):
        """For new records coming from INSPIRE, create and publish a draft in CDS."""
        file_entries = entry["files"].get("entries", None)
        if not file_entries:
            # TODO log the absence of files
            return
            # raise WriterError(f"INSPIRE record #{entry['id']} has no files. Aborting.")
        draft = current_rdm_records_service.create(system_identity, data=entry)

        try:
            for key, file_data in file_entries.items():
                inspire_url = file_data.pop("inspire_url")
                file_content = self._fetch_file(inspire_url)
                if not file_content:
                    return
                self._create_file(file_data, file_content, draft)

        except WriterError as e:
            current_rdm_records_service.delete_draft(system_identity, draft["id"])
            raise e
        else:
            current_rdm_records_service.publish(system_identity, draft["id"])

    def _fetch_file(self, inspire_url, max_retries=3):
        """Fetch file content from inspire url."""
        attempt = 0
        while attempt < max_retries:
            attempt += 1
            try:
                head = requests.head(inspire_url, allow_redirects=True)
                url = head.url
                response = requests.get(url, stream=True)
                if response.status_code == 200:
                    # TODO improve when it makes sense to upload multipart?
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
        # TODO report errors
        # raise WriterError(f"Failed to stream file {inspire_url}. Max retries reached.")

    def _create_file(self, file_data, file_content, draft):
        """Create a new file."""
        service = current_rdm_records_service
        try:
            service.draft_files.init_files(
                system_identity,
                draft.id,
                [file_data],
            )
            service.draft_files.set_file_content(
                system_identity,
                draft.id,
                file_data["key"],
                file_content,
            )
            result = service.draft_files.commit_file(
                system_identity, draft.id, file_data["key"]
            )

            inspire_checksum = file_data["checksum"]
            new_checksum = result.to_dict()["checksum"]
            assert inspire_checksum == new_checksum
        except AssertionError as e:
            ## TODO draft? delete record completely?
            service.draft_files.delete_file(system_identity, draft.id, file_data["key"])
            raise e
