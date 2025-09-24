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
from invenio_rdm_records.services.errors import ValidationErrorWithMessageAsList
from invenio_search.engine import dsl
from invenio_vocabularies.datastreams.errors import WriterError
from invenio_vocabularies.datastreams.writers import BaseWriter
from marshmallow import ValidationError


class InspireWriter(BaseWriter):
    """INSPIRE writer."""

    def _write_entry(self, entry, *args, **kwargs):
        """Write entry to CDS."""
        inspire_id = entry["id"]
        existing_records = self._get_existing_records(inspire_id)
        multiple_records_found = existing_records.total > 1
        should_update = existing_records.total == 1
        should_create = existing_records.total == 0

        existing_records_hits = existing_records.to_dict()["hits"]["hits"]
        existing_records_ids = [hit["id"] for hit in existing_records_hits]

        if multiple_records_found:
            current_app.logger.error(
                f"{existing_records.total} records found on CDS with the same INSPIRE ID ({inspire_id}). Found records ids: {', '.join(existing_records_ids)}."
            )
        elif should_update:
            current_app.logger.info(
                f"INSPIRE record #{inspire_id} has been matched to an existing record #{existing_records_ids[0]}."
            )
            self.update_record(
                entry, record_pid=existing_records_ids[0], inspire_id=inspire_id
            )
            current_app.logger.info(
                f"Record {existing_records_ids[0]} has been successfully updated from INSPIRE #{inspire_id}."
            )
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
        current_app.logger.info(f"All entries processed.")
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

    def update_record(self, entry, record_pid, inspire_id):
        """Update existing record."""
        record = current_rdm_records_service.read(system_identity, record_pid)
        record_dict = record.to_dict()
        existing_files = record_dict["files"]["entries"]
        new_files = entry["files"].get("entries", {})

        # Normalize the checksum format in existing for comparison
        existing_checksums = [
            value["checksum"] for key, value in existing_files.items()
        ]

        current_app.logger.debug(f"Existing files' checksums: {existing_checksums}.")
        new_checksums = [value["checksum"] for key, value in new_files.items()]
        current_app.logger.debug(f"New files' checksums: {new_checksums}.")

        should_create_new_version = existing_checksums != new_checksums

        if should_create_new_version:
            self._create_new_version(entry, record)
        else:
            current_app.logger.info(
                f"No file changes between CDS #{record_dict['id']} and INSPIRE #{inspire_id}. Updating metadata."
            )
            draft = current_rdm_records_service.edit(system_identity, record_pid)
            # TODO make this indempotent
            current_rdm_records_service.update_draft(
                system_identity, draft.id, data=entry
            )
            current_app.logger.info(f"Draft {draft.id} is updated. Publishing it.")

            try:
                current_rdm_records_service.publish(system_identity, draft.id)
                current_app.logger.info(
                    f"Record {record_dict['id']} is successfully updated and published."
                )
            except ValidationError as e:
                current_app.logger.error(
                    f"Draft {record_dict['id']} failed publishing because of validation errors: {e}."
                )
                current_rdm_records_service.delete_draft(system_identity, draft["id"])

    def _create_new_version(self, entry, record):
        """For records with updated files coming from INSPIRE, create and publish a new version."""
        new_version_draft = current_rdm_records_service.new_version(
            system_identity, record.id
        )

        current_app.logger.info(
            f"Differences between existing and new files checksums were found. Draft of a new version of the record "
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

        current_app.logger.info(f"New checksums: {files_to_create}.")
        current_app.logger.info(f"Checksums to delete {files_to_delete}.")

        current_rdm_records_service.import_files(system_identity, new_version_draft.id)

        for filename, file_data in existing_files.items():
            if file_data["checksum"] in files_to_delete:
                current_rdm_records_service.draft_files.delete_file(
                    system_identity, new_version_draft.id, filename
                )

        current_app.logger.info(
            f"{len(existing_files.items())} files have been successfully deleted."
        )

        for key, file in new_files.items():
            if file["checksum"] in files_to_create:
                inspire_url = file.pop("inspire_url")
                file_content = self._fetch_file(inspire_url)
                if not file_content:
                    return
                self._create_file(file, file_content, new_version_draft)
        current_app.logger.info(
            f"{len(new_files.items())} files have been successfully created."
        )

        # update metadata TODO make indempotent
        current_rdm_records_service.update_draft(
            system_identity, new_version_draft.id, entry
        )

        try:
            current_rdm_records_service.publish(system_identity, new_version_draft.id)
            current_app.logger.info(
                f"Metadata is successfully updated and record #{new_version_draft.id} is published."
            )
        except ValidationError as e:
            current_app.logger.error(
                f"Draft {new_version_draft.id} failed publishing because of validation errors: {e}."
            )
            current_rdm_records_service.delete_draft(
                system_identity, new_version_draft.id
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
        file_entries = entry["files"].get("entries", None)
        draft = current_rdm_records_service.create(system_identity, data=entry)
        current_app.logger.info(f"New draft is created ({draft.id}).")
        try:
            current_app.logger.info(
                f"Creating new files for the draft. Filenames: {list(file_entries.keys())}."
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
            current_app.logger.info("Draft is deleted successfully.")
        else:
            try:
                self._add_community(draft)
                current_rdm_records_service.publish(system_identity, draft["id"])
                current_app.logger.info(
                    f"Draft {draft['id']} has been published successfully."
                )
            except ValidationError as e:
                current_app.logger.error(
                    f"Draft {draft['id']} failed publishing because of validation errors: {e}."
                )
                current_rdm_records_service.delete_draft(system_identity, draft["id"])
            except ValidationErrorWithMessageAsList as e:
                current_app.logger.error(
                    f"Draft {draft['id']} failed publishing: {e.messages}."
                )
                current_rdm_records_service.delete_draft(system_identity, draft["id"])

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
                current_app.logger.debug("Retrying in 1 minute...")
                time.sleep(60)

        current_app.logger.error(
            f"Retrieving file request failed. Max retries {max_retries} reached."
            f" URL: {inspire_url}."
        )

    def _create_file(self, file_data, file_content, draft):
        """Create a new file."""
        current_app.logger.debug(
            f"Start creation of a new file. Filename: '{file_data['key']}'."
        )
        service = current_rdm_records_service
        try:
            service.draft_files.init_files(
                system_identity,
                draft.id,
                [file_data],
            )
            current_app.logger.debug(
                f"Init files finished successfully. Filename: '{file_data['key']}'."
            )
            service.draft_files.set_file_content(
                system_identity,
                draft.id,
                file_data["key"],
                file_content,
            )
            current_app.logger.debug(
                f"Set file content finished successfully. Filename: '{file_data['key']}'."
            )
            result = service.draft_files.commit_file(
                system_identity, draft.id, file_data["key"]
            )

            current_app.logger.debug(
                f"Commit file finished successfully. Filename: '{file_data['key']}'."
            )
            inspire_checksum = file_data["checksum"]
            new_checksum = result.to_dict()["checksum"]
            assert inspire_checksum == new_checksum
        except AssertionError as e:
            ## TODO draft? delete record completely?
            current_app.logger.error(
                f"Files checksums don't match. Deleting created file from the draft. Filename: '{file_data['key']}'."
            )
            service.draft_files.delete_file(system_identity, draft.id, file_data["key"])
            current_app.logger.debug(
                f"File is deleted successfully. Filename: '{file_data['key']}'."
            )
            raise e
