# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Transform RDM entry."""
from babel_edtf import parse_edtf
from edtf.parser.grammar import ParseException
from flask import current_app


class RDMEntry:
    """Building of CDS-RDM entry record."""

    def __init__(self, inspire_record):
        """Initializes the RDM entry."""
        self.inspire_record = inspire_record
        self.inspire_metadata = inspire_record["metadata"]
        self.transformer = Inspire2RDM(self.inspire_metadata)
        self.errors = []

    def _id(self):
        return self.inspire_record["id"]

    def _record(self):
        """Transformation of metadata."""
        record, errors = self.transformer.transform_record()
        self.errors.extend(errors)
        return record

    def _files(self):
        """Transformation of files."""
        current_app.logger.info("Start transforming files.")
        files, errors = self.transformer.transform_files()

        current_app.logger.info(
            f"Files transformation finished. Resulting object: {files}."
        )
        current_app.logger.info(f"Files transformation errors: {errors}.")
        self.errors.extend(errors)
        return files

    def _parent(self):
        """Record parent minimal values."""
        current_app.logger.info("Start mounting record parent.")
        parent = {
            "access": {
                "owned_by": {
                    "user": 2,  # temporary solution before we have System user
                }
            }
        }

        current_app.logger.info(f"Record parent is built: {parent}.")
        return parent

    def _access(self):
        """Record access minimal values."""
        current_app.logger.info("Start mounting record and files access level.")
        access = {
            "record": "public",
            "files": "public",
        }

        current_app.logger.info(f"Record access levels are built: {access}.")
        return access

    def build(self):
        """Perform building of CDS-RDM entry record."""
        current_app.logger.info("Start building CDS-RDM entry record.")
        record = self._record()
        rdm_record = {
            "id": self._id(),
            "metadata": record["metadata"],
            "custom_fields": record["custom_fields"],
            "files": self._files(),
            "parent": self._parent(),
            "access": self._access(),
        }

        current_app.logger.info(
            f"Building CDS-RDM entry record finished. RDM record: {rdm_record}."
        )
        current_app.logger.info(f"Errors: {self.errors}.")
        return rdm_record, self.errors


class Inspire2RDM:
    """INSPIRE to CDS-RDM record mapping."""

    def __init__(self, inspire_metadata):
        """Initializes the Inspire2RDM class."""
        self.inspire_metadata = inspire_metadata
        self.metadata_errors = []
        self.files_errors = []

    def _transform_titles(self):
        """Mapping of INSPIRE titles to metadata.title and additional_titles."""
        current_app.logger.info("Start transforming titles.")
        inspire_titles = self.inspire_metadata.get("titles")
        current_app.logger.info(f"Titles from INSPIRE: {inspire_titles}.")
        rdm_title = None
        rdm_additional_titles = []

        for i, inspire_title in enumerate(inspire_titles):
            try:
                if i == 0:
                    rdm_title = inspire_title.get("title")
                    current_app.logger.info(
                        f"The first title is mapped to RDM title: {rdm_title}."
                    )
                else:
                    alt_title = {
                        "title": inspire_title.get("title"),
                        "type": {
                            "id": "alternative-title",
                        },
                    }
                    current_app.logger.info(f"Alternative title mapped: {alt_title}.")
                    rdm_additional_titles.append(alt_title)
                if inspire_title.get("subtitle"):
                    subtitle = {
                        "title": inspire_title.get("subtitle"),
                        "type": {
                            "id": "subtitle",
                        },
                    }
                    current_app.logger.info(f"Subtitle mapped: {subtitle}.")
                    rdm_additional_titles.append(subtitle)
            except Exception as e:
                error_string = f"Error occurred while mapping titles. Title from INSPIRE: {inspire_title}. INSPIRE record id: {self.inspire_metadata.get('control_number')}. Error: {e}."
                current_app.logger.error(error_string)
                self.metadata_errors.append(error_string)
                return None, None

        current_app.logger.info(
            f"Titles transformation finished. Resulting RDM title: {rdm_title}, resulting additional titles: {rdm_additional_titles}."
        )
        return rdm_title, rdm_additional_titles

    def _transform_publication_date(self):
        """Mapping of INSPIRE thesis_info.date to metadata.publication_date."""
        current_app.logger.info("Start transforming publication date.")
        thesis_date = self.inspire_metadata.get("thesis_info", {}).get(
            "date"
        ) or self.inspire_metadata.get("thesis_info", {}).get("defense_date")

        current_app.logger.debug(
            f"Publication date from INSPIRE: {thesis_date}. Parsing to EDTF level 0 format."
        )
        try:
            parsed_date = str(parse_edtf(thesis_date))
            current_app.logger.info(
                f"Publication date transformation finished. Resulting parsed value: {parsed_date}."
            )
            return parsed_date
        except ParseException as e:
            error_string = (
                f"Error occurred while parsing imprint.date to EDTF level 0 format for publication_date. "
                f"INSPIRE record id: {self.inspire_metadata.get('control_number')}. Date: {thesis_date}. "
                f"Error: {e}."
            )
            current_app.logger.error(error_string)
            self.metadata_errors.append(error_string)
            return None

    def _transform_document_type(self):
        """Mapping of INSPIRE document type to resource type."""
        current_app.logger.info("Start transforming document type.")
        document_type = self.inspire_metadata.get("document_type")[0]
        current_app.logger.info(f"Document type from INSPIRE: {document_type}.")
        document_type_mapping = {
            "activity report": "publication-report",
            "article": "publication-article",
            "book": "publication-book",
            "book chapter": "publication-section",
            "conference paper": "publication-conferencepaper",
            "note": "publication-technicalnote",
            "proceedings": "publication-conferenceproceeding",
            "report": "publication-report",
            "thesis": "publication-thesis",
        }

        if document_type not in document_type_mapping:
            error_string = (
                f"Error occurred while mapping document_type to resource_type. Couldn't fine a mapping "
                f"rule for document_type {document_type}. INS"
                f"PIRE record id: {self.inspire_metadata.get('control_number')}."
            )
            current_app.logger.error(error_string)
            self.metadata_errors.append(error_string)
            return None

        result_doc_type = document_type_mapping.get(document_type)
        current_app.logger.info(
            f"Document type transformation finished. Resulting object: {result_doc_type}."
        )
        return result_doc_type

    def _transform_creators(self):
        """Mapping of INSPIRE authors to creators and contributors."""
        current_app.logger.info(
            "Start transforming authors to creators and contributors."
        )
        creators = []
        authors = self.inspire_metadata.get("authors")
        current_app.logger.info(f"Authors from INSPIRE: {authors}.")
        try:
            for author in authors:
                rdm_creator = {
                    "person_or_org": {
                        "type": "personal",
                        "family_name": author.get("last_name"),
                        "given_name": author.get("first_name"),
                        "name": author.get("last_name")
                        + ", "
                        + author.get("first_name"),
                    }
                }
                current_app.logger.info(f"RDM creator mapped: {rdm_creator}.")
                creators.append(rdm_creator)
            current_app.logger.info(
                f"Creators transformation finished. Resulting object: {creators}."
            )
            return creators
        except Exception as e:
            error_string = (
                f"Error occurred while mapping INSPIRE authors to creators and contributors. INSPIRE "
                f"record id: {self.inspire_metadata.get('control_number')}. Error: {e}."
            )
            self.metadata_errors.append(error_string)
            current_app.logger.error(error_string)
            return None

    def _transform_alternate_identifiers(self):
        """Mapping of alternate identifiers."""
        current_app.logger.info("Start transforming alternate identifiers.")
        identifiers = []
        inspire_id = self.inspire_metadata.get("control_number")
        try:
            # add INSPIRE id
            identifiers.append({"identifier": str(inspire_id), "scheme": "inspire"})
            current_app.logger.info(
                f"Alternate identifiers transformation finished. Resulting object: {identifiers}."
            )
            return identifiers
        except Exception as e:
            error_string = f"Error occurred while mapping alternate identifiers. INSPIRE record id: {inspire_id}. Error: {e}."
            current_app.logger.error(error_string)
            self.metadata_errors.append(error_string)
            return None

    def _transform_abstracts(self):
        """Mapping of abstracts."""
        current_app.logger.info("Start transforming abstracts.")
        abstract = self.inspire_metadata["abstracts"][0]["value"]
        current_app.logger.info(
            f"Abstracts transformation finished. Resulting object: {abstract}."
        )
        return abstract

    def _transform_additional_descriptions(self):
        """Mapping of additional descriptions."""
        current_app.logger.info("Start transforming additional descriptions.")
        additional_descriptions = [
            {"description": x["value"], "type": {"id": "abstract"}}
            for x in self.inspire_metadata["abstracts"][1:]
        ]
        if not additional_descriptions:
            current_app.logger.info("No additional descriptions found.")
            return

        current_app.logger.info(
            f"Additional descriptions transformation finished. Resulting object: {additional_descriptions}."
        )
        return additional_descriptions

    def transform_custom_fields(self):
        """Mapping of custom fields."""
        current_app.logger.info("Start transforming custom fields.")
        custom_fields = {}
        # TODO parse legacy name or check with Micha if they can expose name
        accelerators = [
            x.get("accelerator")
            for x in self.inspire_metadata.get("accelerator_experiments", [])
            if x.get("accelerator")
        ]
        experiments = [
            x.get("legacy_name")
            for x in self.inspire_metadata.get("accelerator_experiments", [])
            if x.get("legacy_name")
        ]

        custom_fields["cern:accelerators"] = accelerators
        custom_fields["cern:experiments"] = experiments

        current_app.logger.info(f"Mapped 'accelerators' custom field: {accelerators}.")
        current_app.logger.info(f"Mapped 'experiments' custom field: {experiments}.")
        current_app.logger.info(
            f"Custom fields transformation finished. Resulting object: {custom_fields}."
        )
        return custom_fields

    def transform_metadata(self):
        """Transform INSPIRE metadata."""
        current_app.logger.info("Start record metadata transformation.")
        additional_descriptions = self._transform_additional_descriptions()
        rdm_metadata = {
            "publication_date": self._transform_publication_date(),
            "resource_type": {"id": self._transform_document_type()},
            "creators": self._transform_creators(),
            "identifiers": self._transform_alternate_identifiers(),
            "description": self._transform_abstracts(),
        }
        if additional_descriptions:
            rdm_metadata.update({"additional_descriptions": additional_descriptions})
        title, additional_titles = self._transform_titles()
        rdm_metadata["title"] = title
        if additional_titles:
            rdm_metadata["additional_titles"] = additional_titles

        current_app.logger.info(
            f"Record metadata transformation finished. Resulting object: {rdm_metadata}."
        )
        return rdm_metadata

    def transform_record(self):
        """Perform record transformation."""
        current_app.logger.info("Start record transformation.")
        record = {
            "metadata": self.transform_metadata(),
            "custom_fields": self.transform_custom_fields(),
        }

        current_app.logger.info(
            f"Record transformation finished. Resulting record: {record}."
        )
        current_app.logger.info(f"Metadata errors: {self.metadata_errors}.")
        return record, self.metadata_errors

    def _transform_files(self):
        """Mapping of INSPIRE documents and figures to files."""
        rdm_files_entries = {}
        inspire_files = self.inspire_metadata.get(
            "documents", []
        ) + self.inspire_metadata.get("figures", [])

        current_app.logger.info(f"Documents and figures from INSPIRE: {inspire_files}.")
        if not inspire_files:
            current_app.logger.warning(
                f"INSPIRE record doesn't have any files. Disabling files."
            )
            return {"enabled": False}

        for file in inspire_files:
            try:
                file_details = {
                    "checksum": f"md5:{file['key']}",
                    "key": file["filename"],
                    "access": {"hidden": False},
                    "inspire_url": file["url"],  # put this somewhere else
                }
                rdm_files_entries[file["filename"]] = file_details
                current_app.logger.info(
                    f"File mapped: {file_details}. File name: {file['filename']}."
                )
            except Exception as e:
                error_string = f"Error occurred while mapping files. File key: {file['key']}. INSPIRE record id: {self.inspire_metadata.get('control_number')}. Error: {e}."
                current_app.logger.error(error_string)
                self.files_errors.append(error_string)

        return {
            "enabled": True,
            "entries": rdm_files_entries,
        }

    def transform_files(self):
        """Transform INSPIRE documents and figures."""
        transformed_files = self._transform_files()
        return transformed_files, self.files_errors
