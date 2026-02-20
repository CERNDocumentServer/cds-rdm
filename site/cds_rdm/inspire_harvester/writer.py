# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Writer module."""
import logging
import time
from collections import OrderedDict
from copy import deepcopy
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

from cds_rdm.inspire_harvester.logger import hlog
from cds_rdm.inspire_harvester.update.config import UPDATE_STRATEGY_CONFIG
from cds_rdm.inspire_harvester.update.engine import UpdateContext, UpdateEngine


class InspireWriter(BaseWriter):
    """INSPIRE writer."""

    @hlog
    def _write_entry(self, stream_entry, *args, inspire_id=None, logger=None, **kwargs):
        """Write entry to CDS."""
        existing_records = self._get_existing_records(stream_entry)

        multiple_records_found = existing_records.total > 1
        should_update = existing_records.total == 1
        should_create = existing_records.total == 0

        existing_records_hits = existing_records.to_dict()["hits"]["hits"]
        existing_records_ids = [hit["id"] for hit in existing_records_hits]
        if multiple_records_found:

            msg = "Multiple records match: {0}".format(", ".join(existing_records_ids))

            logger.error(msg)
            stream_entry.errors.append(f"[inspire_id={inspire_id}] {msg}")

            return None

        elif should_update:
            logger.info(f"Matching record found: CDS#{existing_records_ids[0]}")

            self.update_record(
                stream_entry,
                record_pid=existing_records_ids[0],
            )
            return "update"

        elif should_create:
            # no existing record in CDS - create and publish a new one
            self._create_new_record(stream_entry)
            return "create"

        else:
            logger.error(f"Ambiguous action, couldn't determine create or update")
            raise NotImplemented()

    @hlog
    def _process_entry(
        self, stream_entry, *args, inspire_id=None, logger=None, **kwargs
    ):
        """Helper method to process a single entry."""
        error_message = None
        op_type = None

        try:
            op_type = self._write_entry(stream_entry, *args, **kwargs)
        except WriterError as e:
            error_message = f"Error while processing entry : {str(e)}."
        except ValidationError as e:
            error_message = f"Validation error while processing entry: {str(e)}."
        except Exception as e:
            raise e
            # error_message = f"Unexpected error while processing entry: {str(e)}."
        if error_message:
            logger.error(error_message)
            stream_entry.errors.append(f"[inspire_id={inspire_id}] {error_message}")

        stream_entry.op_type = op_type
        return stream_entry

    def write(self, stream_entry, *args, **kwargs):
        """Creates or updates the record in CDS."""
        return self._process_entry(stream_entry, *args, **kwargs)

    def write_many(self, stream_entries, *args, **kwargs):
        """Creates or updates the records in CDS."""
        current_app.logger.debug(f"Start: write_many ({len(stream_entries)} entries)")
        for i, stream_entry in enumerate(stream_entries, 1):
            current_app.logger.debug(f"Processing entry {i}/{len(stream_entries)}")
            self._process_entry(stream_entry, *args, **kwargs)
        current_app.logger.info(f"All entries processed.")
        return stream_entries

    def _retrieve_identifier(self, identifiers, scheme):
        """Retrieve identifier by scheme."""
        return next(
            (d["identifier"] for d in identifiers if d["scheme"] == scheme),
            None,
        )

    @hlog
    def _get_existing_records(
        self, stream_entry, inspire_id=None, logger=None, record_pid=None
    ):
        """Find records that have already been harvested from INSPIRE."""
        entry = stream_entry.entry

        doi = entry.get("pids", {}).get("doi", {}).get("identifier")
        related_identifiers = entry["metadata"].get("related_identifiers", [])

        cds_id = self._retrieve_identifier(related_identifiers, "cds")
        cdsrdm_id = self._retrieve_identifier(related_identifiers, "cdsrdm")
        arxiv_id = self._retrieve_identifier(related_identifiers, "arxiv")
        report_number = self._retrieve_identifier(related_identifiers, "cdsrn")

        doi_filters = [
            dsl.Q("term", **{"pids.doi.identifier.keyword": doi}),
        ]

        cds_filters = [
            dsl.Q("term", **{"id": cdsrdm_id}),
        ]

        inspire_filters = [
            dsl.Q("term", **{"metadata.related_identifiers.scheme": "inspire"}),
            dsl.Q("term", **{"metadata.related_identifiers.identifier": inspire_id}),
        ]

        cds_identifiers_filters = [
            dsl.Q("term", **{"metadata.identifiers.scheme": "cds"}),
            dsl.Q("term", **{"metadata.identifiers.identifier": cds_id}),
        ]

        arxiv_filters = [
            dsl.Q("term", **{"metadata.related_identifiers.scheme": "arxiv"}),
            dsl.Q("term", **{"metadata.related_identifiers.identifier": arxiv_id}),
        ]

        report_number_filters = [
            dsl.Q("term", **{"metadata.related_identifiers.scheme": "cdsrn"}),
            dsl.Q("term", **{"metadata.related_identifiers.identifier": report_number}),
        ]

        filters_priority = OrderedDict(
            doi={"filter": doi_filters, "value": doi},
            cds_pid={"filter": cds_filters, "value": cds_id},
            cds_identifiers={"filter": cds_identifiers_filters, "value": cds_id},
            inspire_id={"filter": inspire_filters, "value": inspire_id},
            arxiv_filters={"filter": arxiv_filters, "value": arxiv_id},
            report_number_filters={
                "filter": report_number_filters,
                "value": report_number,
            },
        )

        for filter_key, filter in filters_priority.items():

            if filter["value"]:
                combined_filter = dsl.Q("bool", filter=filter["filter"])
                logger.debug(f"Searching for existing records: {filter['filter']}")

                result = current_rdm_records_service.search(
                    system_identity, extra_filter=combined_filter
                )

                if result.total >= 1:
                    logger.debug(f"Found {result.total} matching records.")
                    break

        return result

    @hlog
    def update_record(
        self, stream_entry, record_pid=None, inspire_id=None, logger=None
    ):
        """Update existing record."""
        entry = stream_entry.entry

        record = current_rdm_records_service.read(system_identity, record_pid)
        record_dict = record.to_dict()

        existing_files = record_dict["files"]["entries"]
        new_files = entry["files"].get("entries", {})

        logger.info(
            f"Existing files count: {len(existing_files)}, New files count: {len(new_files)}"
        )

        # Normalize the checksum format in existing for comparison
        existing_checksums = [
            value["checksum"] for key, value in existing_files.items()
        ]
        new_checksums = [value["checksum"] for key, value in new_files.items()]

        logger.debug(f"Existing files' checksums: {existing_checksums}.")
        logger.debug(f"New files' checksums: {new_checksums}.")

        existing_record_has_doi = bool(record.data["pids"].get("doi", {}))
        existing_record_has_cds_doi = (
            record.data["pids"].get("doi", {}).get("provider") == "datacite"
        )

        should_update_files = existing_checksums != new_checksums

        should_create_new_version = (
            existing_checksums != new_checksums
            and existing_record_has_doi
            and existing_record_has_cds_doi
        )

        files_enabled = record_dict.get("files", {}).get("enabled", False)

        if should_update_files and not files_enabled:
            stream_entry.entry["files"]["enabled"] = True
            entry["files"]["enabled"] = True

        engine = UpdateEngine(
            strategies=UPDATE_STRATEGY_CONFIG,
            fail_on_conflict=False
        )
        ctx = UpdateContext(source="inspire_import")

        result = engine.update(record_dict, entry, ctx)

        update_metadata = result.updated
        logger.warning(str(result.conflicts))
        logger.info(str(result.audit))

        if should_create_new_version:
            self._create_new_version(stream_entry, update_metadata, record)
        else:
            logger.debug("Create draft for metadata update")

            draft = current_rdm_records_service.edit(system_identity, record_pid)

            logger.debug(f"Draft created with ID: {draft.id}")

            draft = current_rdm_records_service.update_draft(
                system_identity, draft.id, data=update_metadata
            )

            if should_update_files:
                logger.debug(f"Update draft files (due to external DOI): {draft.id}")
                self._update_files(stream_entry, draft, record, record_pid=record.id)

            try:
                logger.debug(f"Publishing updated draft {draft.id}")

                current_rdm_records_service.publish(system_identity, draft.id)

                logger.info(f"Success: Record {record_pid} updated and published.")

            except ValidationError as e:
                logger.error(
                    f"Failure: draft {record_pid} not published, validation errors: {e}."
                )
                current_rdm_records_service.delete_draft(system_identity, draft["id"])
                raise e
            except ValidationErrorWithMessageAsList as e:
                current_rdm_records_service.delete_draft(system_identity, draft["id"])
                raise WriterError(
                    f"ERROR: Draft {draft['id']} not published, validation errors: {e.messages}."
                )
            except Exception as e:
                current_rdm_records_service.delete_draft(system_identity, draft["id"])
                raise WriterError(
                    f"Draft {draft.id} failed publishing because of an unexpected error: {str(e)}."
                )

    @hlog
    def _update_files(
        self,
        stream_entry,
        new_draft,
        record,
        record_pid=None,
        inspire_id=None,
        logger=None,
    ):
        entry = stream_entry.entry
        logger.info("Updating files for record {}".format(record.id))

        record_dict = record.data
        existing_files = record_dict["files"]["entries"]
        new_files = entry["files"].get("entries", {})

        existing_checksums = [
            value["checksum"] for key, value in existing_files.items()
        ]
        new_checksums = [value["checksum"] for key, value in new_files.items()]

        files_to_create = list(set(new_checksums) - set(existing_checksums))
        files_to_delete = list(set(existing_checksums) - set(new_checksums))

        logger.info(
            "New checksums: {files_to_create}.".format(files_to_create=files_to_create),
        )

        logger.info(f"Checksums to delete {files_to_delete}.")

        for filename, file_data in existing_files.items():
            if file_data["checksum"] in files_to_delete:
                logger.debug(f"Delete file: {filename}")

                current_rdm_records_service.draft_files.delete_file(
                    system_identity, new_draft.id, filename
                )

        logger.info(f"{len(existing_files.items())} files successfully deleted.")

        logger.debug("Creating new files")

        for key, file in new_files.items():
            if file["checksum"] in files_to_create:
                logger.debug(f"Processing new file: {key}")
                inspire_url = file.pop("source_url")
                file_content = self._fetch_file(stream_entry, inspire_url)

                if not file_content:
                    logger.error(f"Failed to fetch file content for: {key}")
                    return

                self._create_file(stream_entry, file, file_content, new_draft)
        logger.info(f"{len(new_files.items())} files successfully created.")

    @hlog
    def _create_new_version(
        self, stream_entry, update_metadata, record, inspire_id=None, record_pid=None, logger=None
    ):
        """For records with updated files coming from INSPIRE, create and publish a new version."""
        entry = stream_entry.entry
        new_version_draft = current_rdm_records_service.new_version(
            system_identity, record["id"]
        )

        new_version_entry = deepcopy(update_metadata)
        # delete the previous DOI for new version
        if "pids" in entry:
            del new_version_entry["pids"]

        logger.debug(f"New version draft created with ID: {new_version_draft.id}")

        new_version_draft = current_rdm_records_service.update_draft(
            system_identity, new_version_draft.id, new_version_entry
        )
        if record.data.get("files", {}).get("enabled", False):
            current_rdm_records_service.import_files(
                system_identity, new_version_draft.id
            )
            logger.debug(f"Imported files from previous version: {new_version_draft.id}")

        self._update_files(stream_entry, new_version_draft, record)

        logger.debug(f"New version metadata updated: {new_version_draft.id}")
        try:
            logger.debug("Publishing new version draft")

            current_rdm_records_service.publish(system_identity, new_version_draft.id)

            current_app.logger.info(
                f"New record version #{new_version_draft.id} published."
            )
        except ValidationError as e:
            current_rdm_records_service.delete_draft(
                system_identity, new_version_draft.id
            )
            raise WriterError(
                f"Failure: Draft {new_version_draft.id} not published, validation errors: {e}."
            )
        except ValidationErrorWithMessageAsList as e:
            current_rdm_records_service.delete_draft(
                system_identity, new_version_draft.id
            )
            raise WriterError(
                f"Failure: draft {new_version_draft.id} not published, validation errors: {e.messages}."
            )

    @hlog
    def _add_community(
        self, stream_entry, draft, inspire_id=None, record_pid=None, logger=None
    ):
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

    @hlog
    def _create_new_record(
        self, stream_entry, record_pid=None, inspire_id=None, logger=None
    ):
        """For new records coming from INSPIRE, create and publish a draft in CDS."""
        entry = stream_entry.entry

        doi = entry.get("pids", {}).get("doi", {})
        DATACITE_PREFIX = current_app.config["DATACITE_PREFIX"]
        is_cds = DATACITE_PREFIX in doi.get("identifier", "")
        if is_cds:
            raise WriterError("Trying to create record with CDS DOI")

        file_entries = entry["files"].get("entries", None)
        logger.debug(f"Files to create: {len(file_entries) if file_entries else 0}")

        logger.debug("Creating new record draft")

        draft = current_rdm_records_service.create(system_identity, data=entry)

        logger.info(f"New draft is created ({draft.id}).")

        try:
            if file_entries:
                logger.info(
                    f"Creating new files. Filenames: {list(file_entries.keys())}."
                )

                for key, file_data in file_entries.items():
                    logger.debug(f"Processing file: {key}")

                    inspire_url = file_data.pop("source_url", None)
                    file_content = self._fetch_file(stream_entry, inspire_url)
                    if not file_content:
                        logger.error(f"Failed to fetch file content for: {key}")

                        return

                    self._create_file(stream_entry, file_data, file_content, draft)
                logger.info(f"All the files successfully created.")

        except Exception as e:

            current_rdm_records_service.delete_draft(system_identity, draft["id"])
            logger.error(f"Draft {draft.id} is deleted due to errors.")
            raise e
        else:
            try:
                self._add_community(stream_entry, draft)

                logger.debug(f"Publish draft {draft.id}...")

                current_rdm_records_service.publish(system_identity, draft["id"])

                logger.info(f"Draft {draft['id']} published successfully.")

            except ValidationError as e:
                current_rdm_records_service.delete_draft(system_identity, draft["id"])
                raise WriterError(
                    f"Failure: draft {draft['id']} not published, validation errors: {e}."
                )
            except ValidationErrorWithMessageAsList as e:
                current_rdm_records_service.delete_draft(system_identity, draft["id"])
                raise WriterError(
                    f"Failure: draft {draft['id']} not published, validation errors: {e.messages}."
                )
            except Exception as e:
                current_rdm_records_service.delete_draft(system_identity, draft["id"])
                raise e

    @hlog
    def _fetch_file(
        self,
        stream_entry,
        inspire_url,
        max_retries=3,
        inspire_id=None,
        record_pid=None,
        logger=None,
    ):
        """Fetch file content from inspire url."""
        logger.debug(f"File URL: {inspire_url}")
        attempt = 0
        while attempt < max_retries:
            attempt += 1
            try:
                logger.debug(
                    f"Attempt {attempt}/{max_retries} - HEAD request to: {inspire_url}"
                )
                head = requests.head(inspire_url, allow_redirects=True)
                url = head.url
                logger.info(f"Get file, URL: {url}.")
                response = requests.get(url, stream=True)

                logger.debug(f"Response status code: {response.status_code}")
                if response.status_code == 200:
                    # TODO improve when it makes sense to upload multipart?
                    logger.debug("Success: File retrieved.")
                    return BytesIO(response.content)
                else:
                    logger.warning(
                        f"Retrieving file request failed. "
                        f"Attempt {attempt}/{max_retries} "
                        f"Error {response.status_code}."
                        f" URL: {url}."
                    )
            except Exception as e:
                logger.warning(
                    f"Attempt {attempt}/{max_retries} failed with exception: {e}"
                )
                logger.debug("Retrying in 1 minute...")
                time.sleep(60)

        logger.error(
            f"Retrieving file request failed. Max retries {max_retries} reached."
            f" URL: {inspire_url}."
        )

    @hlog
    def _create_file(
        self,
        stream_entry,
        file_data,
        file_content,
        draft,
        inspire_id=None,
        record_pid=None,
        logger=None,
    ):
        """Create a new file."""
        logger.debug(f"Filename: '{file_data['key']}'.")
        service = current_rdm_records_service
        inspire_checksum = file_data["checksum"]
        file_source = file_data.get("source")
        new_checksum = None

        try:
            service.draft_files.init_files(
                system_identity,
                draft.id,
                [file_data],
            )

            logger.debug(f"Filename: '{file_data['key']}' initialized successfully.")
            service.draft_files.set_file_content(
                system_identity,
                draft.id,
                file_data["key"],
                file_content,
            )

            logger.debug(
                f"Filename: '{file_data['key']}' content set successfully. Commit file..."
            )
            result = service.draft_files.commit_file(
                system_identity, draft.id, file_data["key"]
            )

            new_checksum = result.data["checksum"]

            logger.debug(
                f"Filename: '{file_data['key']}' committed. File checksum: {result.data['checksum']}."
            )
            if file_source != "arxiv":
                # arxiv files do not expose checksum via their API
                assert inspire_checksum == new_checksum
            elif inspire_checksum and file_source == "arxiv":
                assert inspire_checksum == new_checksum
        except AssertionError as e:
            ## TODO draft? delete record completely?
            logger.error(
                f"Files checksums don't match. Delete file: '{file_data['key']}' from draft."
            )

            service.draft_files.delete_file(system_identity, draft.id, file_data["key"])

            raise WriterError(
                f"File {file_data['key']} checksum mismatch. Expected: {inspire_checksum}, got: {new_checksum}."
            )