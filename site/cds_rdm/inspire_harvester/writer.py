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
from invenio_records_resources.services.errors import FileKeyNotFoundError
from invenio_vocabularies.datastreams.errors import WriterError
from invenio_vocabularies.datastreams.writers import BaseWriter


class InspireWriter(BaseWriter):
    """INSPIRE writer."""

    def _write_entry(self, entry, *args, **kwargs):
        identifiers = entry["metadata"].get("identifiers", {})
        inspire_id = next(
            (item["identifier"] for item in identifiers if item["scheme"] == "inspire"),
            None,
        )

        existing_records = self._get_existing_records(inspire_id)
        existing_records_hits = existing_records.to_dict()["hits"]["hits"]
        existing_records_ids = [hit["id"] for hit in existing_records_hits]
        if existing_records.total > 1:
            raise WriterError(
                f"More than 1 record found with INSPIRE id {inspire_id}. CDS records found: {', '.join(existing_records_ids)}"
            )
        elif existing_records.total == 1:
            self._handle_existing_records(
                entry, existing_records_ids[0], existing_records_hits, inspire_id
            )
        else:
            # no existing record in CDS - create and publish a new one
            self._create_new_record(inspire_id, entry)

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

    def _handle_existing_records(
        self, entry, existing_rec_id, existing_records_hits, inspire_id
    ):
        existing_entries = existing_records_hits[0]["files"]["entries"]
        new_entries = entry["files"].get("entries", {})

        # Normalize the checksum format in existing for comparison
        existing_checksums = {
            key: value["checksum"].replace("md5:", "")
            for key, value in existing_entries.items()
        }
        new_checksums = {key: value["checksum"] for key, value in new_entries.items()}

        # Find key-value pairs in new entry but not in existing
        only_in_entry = {
            key: value
            for key, value in new_entries.items()
            if new_checksums[key] not in existing_checksums.values()
        }

        # Find file keys in existing but not in new entry
        only_in_existing = [
            key
            for key, value in existing_entries.items()
            if existing_checksums[key] not in new_checksums.values()
        ]

        differences = len(only_in_entry) + len(only_in_existing)
        if differences:
            new_version_success = self._create_new_version(
                only_in_entry, only_in_existing, inspire_id, entry, existing_rec_id
            )
            if not new_version_success:
                return False
        else:
            current_rdm_records_service.edit(system_identity, existing_rec_id)
            current_rdm_records_service.update_draft(
                system_identity, existing_rec_id, entry
            )
            current_rdm_records_service.publish(system_identity, existing_rec_id)

    def _create_new_version(
        self, only_in_entry, only_in_existing, inspire_id, entry, existing_rec_id
    ):
        """For records with updated files coming from INSPIRE, create and publish a new version."""
        new_version_draft = current_rdm_records_service.new_version(
            system_identity, existing_rec_id
        )
        draft_id = new_version_draft.to_dict()["id"]
        files_enabled = new_version_draft.to_dict()["files"]["enabled"]

        if files_enabled:
            current_rdm_records_service.import_files(system_identity, draft_id)

        if only_in_entry:
            try:
                if not files_enabled:
                    draft = new_version_draft._record
                    draft.files.enabled = True
                    draft.commit()

                self._create_files(only_in_entry, draft_id, inspire_id)
            except WriterError:
                current_rdm_records_service.delete_draft(system_identity, draft_id)
                return False

        if only_in_existing:
            for key in only_in_existing:
                current_rdm_records_service.draft_files.delete_file(
                    system_identity, draft_id, key
                )

        # update metadata as well
        current_rdm_records_service.update_draft(system_identity, draft_id, entry)
        current_rdm_records_service.publish(system_identity, draft_id)
        return True

    def _create_new_record(self, inspire_id, entry):
        """For new records coming from INSPIRE, create and publish a draft in CDS."""
        draft = current_rdm_records_service.create(system_identity, data=entry)
        file_entries = entry["files"].get("entries", None)
        if file_entries:
            try:
                self._create_files(file_entries, draft["id"], inspire_id)
            except WriterError:
                current_rdm_records_service.delete_draft(system_identity, draft["id"])
                return False

        current_rdm_records_service.publish(system_identity, draft["id"])
        return True

    def _get_existing_records(self, inspire_id):
        """Find records that have already been harvested from INSPIRE."""
        # for now checking only by inspire id
        return current_rdm_records_service.search(
            system_identity,
            params={
                "q": f"metadata.identifiers.identifier:{inspire_id} AND metadata.identifiers.scheme:inspire"
            },
        )

    def _create_files(self, files_to_add, draft_id, inspire_id):
        """Add and commit files to a draft."""
        max_retries = 3
        service = current_rdm_records_service
        for _, file in files_to_add.items():
            attempt = 0
            url = file.pop("inspire_url")
            while attempt < max_retries:
                try:
                    attempt += 1
                    response = requests.get(url, stream=True)
                    if response.status_code == 200:
                        service.draft_files.init_files(
                            system_identity,
                            draft_id,
                            [file],
                        )
                        content = BytesIO(response.content)
                        service.draft_files.set_file_content(
                            system_identity,
                            draft_id,
                            file["key"],
                            content,
                        )
                        result = service.draft_files.commit_file(
                            system_identity, draft_id, file["key"]
                        )

                        inspire_checksum = f"md5:{file['checksum']}"
                        new_checksum = result.to_dict()["checksum"]
                        assert inspire_checksum == new_checksum
                        break
                    else:
                        current_app.logger.error(
                            f"Retrieving file request failed on attempt {attempt}. Max "
                            f"retries: {max_retries}. Status: {response.status_code}. "
                            f"Response: {response.text}. URL: {url}. Filename: "
                            f"{file['key']}. INSPIRE record id: {inspire_id}."
                        )

                        if attempt < max_retries:
                            current_app.logger.error("Retrying in 1 minute...")
                            time.sleep(60)
                except Exception as e:
                    current_app.logger.error(
                        f"Retrieving file request failed on attempt {attempt}. Max retries: {max_retries}. Error {e}. URL: {url}. Filename: {file['key']}. INSPIRE record id: {inspire_id}."
                    )

                    try:
                        if attempt < max_retries:
                            current_app.logger.error("Retrying in 1 minute...")
                            time.sleep(60)
                            service.draft_files.delete_file(
                                system_identity, draft_id, file["key"]
                            )
                            continue
                    except FileKeyNotFoundError:
                        continue
                raise WriterError(f"Failed to stream file {file}. Max retries reached.")
