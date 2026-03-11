# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""File synchronization module."""

import time
from dataclasses import dataclass
from io import BytesIO
from typing import List

import requests
from invenio_access.permissions import system_identity
from invenio_rdm_records.proxies import current_rdm_records_service
from invenio_records_resources.services.errors import FileKeyNotFoundError
from invenio_vocabularies.datastreams.errors import WriterError


@dataclass
class RetryConfig:
    """Configuration for file fetch retries."""

    max_retries: int = 3
    retry_delay: int = 60  # seconds; only applied on network exceptions


@dataclass
class FileDiff:
    """Diff between existing and new file sets, keyed by checksum."""

    to_add: List[str]  # checksums of new files to upload
    to_delete: List[str]  # checksums of files to remove
    existing: List[str]


class FileSynchronizer:
    """Handles file I/O, diffing, uploading, and deletion for draft records."""

    def __init__(self, retry_config: RetryConfig = None):
        """Constructor."""
        self.retry_config = retry_config or RetryConfig()

    def compute_diff(self, existing_files, new_files) -> FileDiff:
        """Return the set difference between existing and new file checksums."""

        existing_checksums = [value["checksum"] for value in existing_files.values()]
        new_checksums = [value["checksum"] for value in new_files.values()]

        return FileDiff(
            to_add=list(set(new_checksums) - set(existing_checksums)),
            to_delete=list(set(existing_checksums) - set(new_checksums)),
            existing=list(set(existing_checksums))
        )

    def fetch(self, url, logger) -> BytesIO:
        """Fetch file content from URL.

        Raises WriterError after exhausting retries.
        """
        max_retries = self.retry_config.max_retries
        retry_delay = self.retry_config.retry_delay

        logger.debug(f"File URL: {url}")
        attempt = 0
        while attempt < max_retries:
            attempt += 1
            try:
                logger.debug(
                    f"Attempt {attempt}/{max_retries} - HEAD request to: {url}"
                )
                head = requests.head(url, allow_redirects=True)
                resolved_url = head.url
                logger.info(f"Get file, URL: {resolved_url}.")
                response = requests.get(resolved_url, stream=True)
                logger.debug(f"Response status code: {response.status_code}")
                if response.status_code == 200:
                    logger.debug("Success: File retrieved.")
                    return BytesIO(response.content)
                else:
                    logger.warning(
                        f"Retrieving file request failed. "
                        f"Attempt {attempt}/{max_retries} "
                        f"Error {response.status_code}."
                        f" URL: {resolved_url}."
                    )
            except Exception as e:
                logger.warning(
                    f"Attempt {attempt}/{max_retries} failed with exception: {e}"
                )
                logger.debug("Retrying in 1 minute...")
                time.sleep(retry_delay)

        logger.error(
            f"Retrieving file request failed. Max retries {max_retries} reached."
            f" URL: {url}."
        )
        raise WriterError(
            f"Failed to fetch file from {url} after {max_retries} retries."
        )

    def check_files_should_update(self, record, incoming_record, logger):
        record_dict = record.to_dict()
        existing_files = record_dict["files"]["entries"]
        new_files = incoming_record["files"].get("entries", {})
        logger.info(
            f"Existing files count: {len(existing_files)},"
            f" New files count: {len(new_files)}"
        )

        diff = self.compute_diff(existing_files, new_files)
        logger.debug(f"Existing files' checksums: {diff.existing}.")
        logger.debug(f"New files' checksums: {diff.to_add}.")

        should_update_files = bool(new_files) and diff.existing != diff.to_add

        return should_update_files

    def sync(self, draft, record, incoming_record, logger, import_files=True):
        """Sync files on a draft: delete removed files, upload added files."""
        should_import_files = (record and import_files and
                               record.data.get("files", {}).get("enabled", False))
        existing_files = []
        if should_import_files:
            record_dict = record.to_dict()
            existing_files = record_dict["files"]["entries"]
            current_rdm_records_service.import_files(system_identity, draft.id)
            logger.debug(
                f"Imported files to {draft.id} from previous version: {record.id}")

        new_files = incoming_record["files"].get("entries", {})
        logger.info(
            f"Existing files count: {len(existing_files)},"
            f" New files count: {len(new_files)}"
        )

        diff = self.compute_diff(existing_files, new_files)

        logger.info(f"New checksums: {diff.to_add}.")
        logger.info(f"Checksums to delete {diff.to_delete}.")

        for filename, file_data in existing_files.items():
            if file_data["checksum"] in diff.to_delete:
                logger.debug(f"Delete file: {filename}")
                current_rdm_records_service.draft_files.delete_file(
                    system_identity, draft.id, filename
                )
        logger.info(f"{len(diff.to_delete)} files successfully deleted.")

        logger.debug("Creating new files")
        for key, file in new_files.items():
            if file["checksum"] in diff.to_add:
                logger.debug(f"Processing new file: {key}")
                inspire_url = file.pop("source_url")
                file_content = self.fetch(inspire_url, logger)
                self._upload_file(draft, file, file_content, logger)
        logger.info(f"{len(new_files)} files successfully created.")

    def _upload_file(self, draft, file_data, file_content, logger):
        """Initialize, upload, and commit a single file to the draft."""
        logger.debug(f"Filename: '{file_data['key']}'.")
        service = current_rdm_records_service
        inspire_checksum = file_data["checksum"]
        new_checksum = None

        try:
            if inspire_checksum is None:
                # this can happen when we get the file directly from arxiv.
                # unfortunately, arxiv does not expose checksums
                del file_data["checksum"]
            service.draft_files.init_files(system_identity, draft.id, [file_data])
            logger.debug(f"Filename: '{file_data['key']}' initialized successfully.")

            service.draft_files.set_file_content(
                system_identity, draft.id, file_data["key"], file_content
            )
            logger.debug(
                f"Filename: '{file_data['key']}' content set successfully. Commit file..."
            )

            result = service.draft_files.commit_file(
                system_identity, draft.id, file_data["key"]
            )
            new_checksum = result.data["checksum"]
            logger.debug(
                f"Filename: '{file_data['key']}' committed."
                f" File checksum: {result.data['checksum']}."
            )

            if inspire_checksum:
                assert inspire_checksum == new_checksum
        except AssertionError:
            logger.error(
                f"Files checksums don't match."
                f" Delete file: '{file_data['key']}' from draft."
            )
            service.draft_files.delete_file(system_identity, draft.id, file_data["key"])
            raise WriterError(
                f"File {file_data['key']} checksum mismatch."
                f" Expected: {inspire_checksum}, got: {new_checksum}."
            )
