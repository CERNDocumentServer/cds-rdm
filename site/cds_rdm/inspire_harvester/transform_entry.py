# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Transform RDM entry."""
from babel_edtf import parse_edtf
from edtf.parser.grammar import ParseException


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
        files, errors = self.transformer.transform_files()
        self.errors.extend(errors)
        return files

    def _parent(self):
        """Record parent minimal values."""
        return {
            "access": {
                "owned_by": {
                    "user": 2,  # temporary solution before we have System user
                }
            }
        }

    def _access(self):
        """Record access minimal values."""
        return {
            "record": "public",
            "files": "public",
        }

    def build(self):
        """Perform building of CDS-RDM entry record."""
        record = self._record()
        rdm_record = {
            "id": self._id(),
            "metadata": record["metadata"],
            "custom_fields": record["custom_fields"],
            "files": self._files(),
            "parent": self._parent(),
            "access": self._access(),
        }

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
        inspire_titles = self.inspire_metadata.get("titles")
        rdm_title = None
        rdm_additional_titles = []

        for i, inspire_title in enumerate(inspire_titles):
            try:
                if i == 0:
                    rdm_title = inspire_title.get("title")
                else:
                    rdm_additional_titles.append(
                        {
                            "title": inspire_title.get("title"),
                            "type": {
                                "id": "alternative-title",
                            },
                        }
                    )

                if inspire_title.get("subtitle"):
                    rdm_additional_titles.append(
                        {
                            "title": inspire_title.get("subtitle"),
                            "type": {
                                "id": "subtitle",
                            },
                        }
                    )
            except Exception as e:
                self.metadata_errors.append(
                    f"Error occurred while mapping titles. Title from INSPIRE: {inspire_title}. INSPIRE record id: {self.inspire_metadata.get('control_number')}. Error: {e}."
                )
                return None, None

        return rdm_title, rdm_additional_titles

    def _transform_publication_date(self):
        """Mapping of INSPIRE thesis_info.date to metadata.publication_date."""
        thesis_date = self.inspire_metadata.get("thesis_info", {}).get(
            "date"
        ) or self.inspire_metadata.get("thesis_info", {}).get("defense_date")
        try:
            parsed_date = str(parse_edtf(thesis_date))
            return parsed_date
        except ParseException as e:
            self.metadata_errors.append(
                f"Error occurred while parsing imprint.date to EDTF level 0 format for publication_date. INSPIRE "
                f"record id: {self.inspire_metadata.get('control_number')}. Date: {thesis_date}. Error: {e}."
            )
            return None

    def _transform_document_type(self):
        """Mapping of INSPIRE document type to resource type."""
        document_type = self.inspire_metadata.get("document_type")[0]

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
            self.metadata_errors.append(
                f"Error occurred while mapping document_type to resource_type. Couldn't fine a mapping rule for "
                f"document_type {document_type}. INSPIRE record id: {self.inspire_metadata.get('control_number')}."
            )
            return None

        return document_type_mapping.get(document_type)

    def _transform_creators(self):
        """Mapping of INSPIRE authors to creators and contributors."""
        creators = []
        authors = self.inspire_metadata.get("authors")
        try:
            for author in authors:
                creators.append(
                    {
                        "person_or_org": {
                            "type": "personal",
                            "family_name": author.get("last_name"),
                            "given_name": author.get("first_name"),
                            "name": author.get("last_name")
                            + ", "
                            + author.get("first_name"),
                        }
                    }
                )
            return creators
        except Exception as e:
            self.metadata_errors.append(
                f"Error occurred while mapping INSPIRE authors to creators and contributors. INSPIRE record id: {self.inspire_metadata.get('control_number')}. Error: {e}."
            )
            return None

    def _transform_alternate_identifiers(self):
        """Mapping of alternate identifiers."""
        identifiers = []
        inspire_id = self.inspire_metadata.get("control_number")
        try:
            # add INSPIRE id
            identifiers.append({"identifier": str(inspire_id), "scheme": "inspire"})
            return identifiers
        except Exception as e:
            self.metadata_errors.append(
                f"Error occurred while mapping alternate identifiers. INSPIRE record id: {inspire_id}. Error: {e}."
            )
            return None

    def _transform_abstracts(self):
        """Mapping of abstracts."""
        abstract = self.inspire_metadata["abstracts"][0]["value"]

        return abstract

    def _transform_additional_descriptions(self):
        """Mapping of additional descriptions."""
        additional_descriptions = [
            {"description": x["value"], "type": {"id": "abstract"}}
            for x in self.inspire_metadata["abstracts"][1:]
        ]
        if not additional_descriptions:
            return
        return additional_descriptions

    def transform_custom_fields(self):
        """Mapping of custom fields."""
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
        return custom_fields

    def transform_metadata(self):
        """Transform INSPIRE metadata."""
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

        return rdm_metadata

    def transform_record(self):
        """Perform record transformation."""
        record = {
            "metadata": self.transform_metadata(),
            "custom_fields": self.transform_custom_fields(),
        }
        return record, self.metadata_errors

    def _transform_files(self):
        """Mapping of INSPIRE documents and figures to files."""
        rdm_files_entries = {}
        inspire_files = self.inspire_metadata.get(
            "documents", []
        ) + self.inspire_metadata.get("figures", [])

        if not inspire_files:
            return {"enabled": False}

        for file in inspire_files:
            try:
                rdm_files_entries[file["filename"]] = {
                    "checksum": f"md5:{file['key']}",
                    "key": file["filename"],
                    "access": {"hidden": False},
                    "inspire_url": file["url"],  # put this somewhere else
                }
            except Exception as e:
                self.files_errors.append(
                    f"Error occurred while mapping files. File key: {file['key']}. INSPIRE record id: {self.inspire_metadata.get('control_number')}. Error: {e}."
                )

        return {
            "enabled": True,
            "entries": rdm_files_entries,
        }

    def transform_files(self):
        """Transform INSPIRE documents and figures."""
        transformed_files = self._transform_files()
        return transformed_files, self.files_errors
