# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Transform RDM entry."""
import json
from copy import deepcopy

import pycountry
from babel_edtf import parse_edtf
from edtf.parser.grammar import ParseException
from flask import current_app
from idutils.normalizers import normalize_isbn
from idutils.validators import is_doi
from invenio_access.permissions import system_identity, system_user_id
from invenio_records_resources.proxies import current_service_registry
from opensearchpy import RequestError
from sqlalchemy.orm.exc import NoResultFound

from cds_rdm.inspire_harvester.logger import Logger

# Mapping from INSPIRE document types to CDS-RDM resource types
INSPIRE_DOCUMENT_TYPE_MAPPING = {
    "article": "publication-article",
    "book": "publication-book",
    "report": "publication-report",
    "proceedings": "publication-conferenceproceeding",
    "book chapter": "publication-section",
    "thesis": "publication-dissertation",
    "note": "publication-technicalnote",
    "conference paper": "publication-conferencepaper",
}


class RDMEntry:
    """Building of CDS-RDM entry record."""

    def __init__(self, inspire_record):
        """Initializes the RDM entry."""
        self.inspire_record = inspire_record
        self.inspire_metadata = inspire_record["metadata"]
        self.transformer = Inspire2RDM(self.inspire_record)
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
        parent = {
            "access": {
                "owned_by": {
                    "user": system_user_id,
                }
            }
        }
        return parent

    def _access(self):
        """Record access minimal values."""
        access = {
            "record": "public",
            "files": "public",
        }
        return access

    def build(self):
        """Perform building of CDS-RDM entry record."""
        inspire_id = self.inspire_record.get("id")
        current_app.logger.debug(
            f"[inspire_id={inspire_id}] Starting build of CDS-RDM entry record"
        )

        inspire_files = self.inspire_metadata.get("documents", [])
        current_app.logger.debug(
            f"[inspire_id={inspire_id}] Found {len(inspire_files)} files in INSPIRE record"
        )

        if not inspire_files:
            current_app.logger.warning(
                f"[inspire_id={inspire_id}] No files found in INSPIRE record - aborting transformation"
            )
            self.errors.append(
                f"INSPIRE record #{self.inspire_metadata['control_number']} has no files. Metadata-only records are not supported. Aborting record transformation."
            )
            return None, self.errors

        current_app.logger.debug(
            f"[inspire_id={inspire_id}] Starting record metadata transformation"
        )
        record = self._record()
        current_app.logger.debug(
            f"[inspire_id={inspire_id}] Record metadata transformation completed"
        )

        current_app.logger.debug(
            f"[inspire_id={inspire_id}] Starting files transformation"
        )
        files = self._files()
        current_app.logger.debug(
            f"[inspire_id={inspire_id}] Files transformation completed"
        )

        rdm_record = {
            "id": self._id(),
            "metadata": record["metadata"],
            "custom_fields": record["custom_fields"],
            "files": files,
            "parent": self._parent(),
            "access": self._access(),
        }

        if record.get("pids"):
            rdm_record["pids"] = record["pids"]

        current_app.logger.debug(
            f"[inspire_id={inspire_id}] Building CDS-RDM entry record finished. RDM record: {rdm_record}."
        )
        return rdm_record, self.errors


class Inspire2RDM:
    """INSPIRE to CDS-RDM record mapping."""

    def __init__(self, inspire_record):
        """Initializes the Inspire2RDM class."""
        self.inspire_record = inspire_record
        self.inspire_original_metadata = inspire_record["metadata"]
        self.inspire_metadata = deepcopy(inspire_record["metadata"])
        self.inspire_id = self.inspire_record.get("id")
        self.logger = Logger(inspire_id=self.inspire_id)
        self.metadata_errors = []
        self.files_errors = []

        self._get_cds_id()
        self._clean_data()

        # pre-clean data

    def _clean_data(self):
        self._clean_identifiers()

    def _get_cds_id(self):
        """Get CDS ID from INSPIRE metadata."""
        external_sys_ids = self.inspire_metadata.get("external_system_identifiers", [])
        for external_sys_id in external_sys_ids:
            schema = external_sys_id.get("schema")
            if schema.upper() in ["CDS", "CDSRDM"]:
                self.cds_id = external_sys_id.get("value")

    def _clean_identifiers(self):
        IDENTIFIERS_SCHEMES_TO_DROP = [
            "SPIRES",
            "HAL",
            "OSTI",
            "SLAC",
            "PROQUEST",
        ]
        external_sys_ids = self.inspire_metadata.get("external_system_identifiers", [])
        persistent_ids = self.inspire_metadata.get("persistent_identifiers", [])

        cleaned_external_sys_ids = []
        cleaned_persistent_ids = []

        for external_sys_id in external_sys_ids:
            schema = external_sys_id.get("schema")
            if schema.upper() not in IDENTIFIERS_SCHEMES_TO_DROP:
                cleaned_external_sys_ids.append(external_sys_id)
        for persistent_id in persistent_ids:
            schema = persistent_id.get("schema")

            if schema.upper() not in IDENTIFIERS_SCHEMES_TO_DROP:
                cleaned_persistent_ids.append(persistent_id)

        self.inspire_metadata["external_system_identifiers"] = cleaned_external_sys_ids
        self.inspire_metadata["persistent_identifiers"] = cleaned_persistent_ids

    def _transform_titles(self):
        """Mapping of INSPIRE titles to metadata.title and additional_titles."""
        inspire_titles = self.inspire_metadata.get("titles", [])
        rdm_title = None
        rdm_additional_titles = []

        for i, inspire_title in enumerate(inspire_titles):
            try:
                if i == 0:
                    rdm_title = inspire_title.get("title")
                else:
                    alt_title = {
                        "title": inspire_title.get("title"),
                        "type": {
                            "id": "alternative-title",
                        },
                    }
                    rdm_additional_titles.append(alt_title)
                if inspire_title.get("subtitle"):
                    subtitle = {
                        "title": inspire_title.get("subtitle"),
                        "type": {
                            "id": "subtitle",
                        },
                    }
                    rdm_additional_titles.append(subtitle)
            except Exception as e:
                self.metadata_errors.append(
                    f"Title {inspire_title} transform failed. INSPIRE#{self.inspire_id}. Error: {e}."
                )
                return None, None

        return rdm_title, rdm_additional_titles

    def _validate_imprint(self):
        """Validate that record has only 1 imprint."""
        imprints = self.inspire_metadata.get("imprints", [])

        if not imprints:
            return
        if len(imprints) > 1:
            self.metadata_errors.append(
                f"More than 1 imprint found. INSPIRE#{self.inspire_id}."
            )
            return

        return imprints[0]

    def _transform_publisher(self):
        """Mapping of publisher."""
        imprint = self._validate_imprint()
        DATACITE_PREFIX = current_app.config["DATACITE_PREFIX"]
        dois = self.inspire_metadata.get("dois", [])

        has_cds_doi = next(
            (d["value"] for d in dois if d["value"].startswith(DATACITE_PREFIX)),
            False,
        )
        if has_cds_doi and not imprint.get("publisher"):
            return "CERN"
        elif not imprint:
            return
        return imprint.get("publisher")

    def _transform_publication_date(self):
        """Mapping of INSPIRE thesis_info.date to metadata.publication_date."""
        imprint = self._validate_imprint()

        thesis_info = self.inspire_metadata.get("thesis_info", {})
        thesis_date = thesis_info.get("date") or (
            imprint.get("date") if imprint else None
        )

        if thesis_date is None:
            self.metadata_errors.append(
                f"Thesis publication date transform failed. INSPIRE#{self.inspire_id}."
            )
            return None
        try:
            parsed_date = str(parse_edtf(thesis_date))
            return parsed_date
        except ParseException as e:
            self.metadata_errors.append(
                f"Publication date transformation failed."
                f"INSPIRE#{self.inspire_metadata['control_number']}. Date: {thesis_date}. "
                f"Error: {e}."
            )
            return None

    def _transform_document_type(self):
        """Mapping of INSPIRE document type to resource type."""
        inspire_id = self.inspire_id
        document_types = self.inspire_metadata.get("document_type", [])

        self.logger.debug(f"Processing document types: {document_types}")

        if not document_types:
            self.metadata_errors.append(
                f"No document_type found in INSPIRE#{inspire_id}."
            )
            return None

        # Check for multiple document types - fail for now
        if len(document_types) > 1:
            self.metadata_errors.append(
                f"Multiple document types found: {document_types}. INSPIRE#: {inspire_id}. "
                f"Multiple document types are not supported yet."
            )
            self.logger.error(f"Multiple document types found: {document_types}")
            return None

        # Get the single document type
        document_type = document_types[0]
        self.logger.debug(f"Document type found: {document_type}")

        # Use the reusable mapping
        if document_type not in INSPIRE_DOCUMENT_TYPE_MAPPING:
            self.metadata_errors.append(
                f"Error: Couldn't find resource type mapping rule for "
                f"document_type '{document_type}'. INSPIRE#{inspire_id}. "
                f"Available mappings: {list(INSPIRE_DOCUMENT_TYPE_MAPPING.keys())}"
            )
            self.logger.error(f"Unmapped document type: {document_type}")
            return None

        mapped_resource_type = INSPIRE_DOCUMENT_TYPE_MAPPING[document_type]
        self.logger.info(
            f"Mapped document type '{document_type}' to resource type '{mapped_resource_type}'"
        )

        return {"id": mapped_resource_type}

    def _transform_contributors(self):
        """Mapping of INSPIRE authors to contributors."""
        authors = self.inspire_metadata.get("authors", [])
        contributors = []

        for author in authors:
            inspire_roles = author.get("inspire_roles", [])
            if "supervisor" in inspire_roles:
                contributors.append(author)

        return self._transform_creatibutors(contributors)

    def _transform_creators(self):
        """Mapping of INSPIRE authors to creators."""
        authors = self.inspire_metadata.get("authors", [])
        creators = []
        for author in authors:
            inspire_roles = author.get("inspire_roles")
            if not inspire_roles:
                creators.append(author)
            elif "author" in inspire_roles or "editor" in inspire_roles:
                creators.append(author)

        corporate_authors = self.inspire_metadata.get("corporate_author", [])
        mapped_corporate_authors = []
        for corporate_author in corporate_authors:
            contributor = {
                "person_or_org": {
                    "type": "organizational",
                    "name": corporate_author,
                },
            }
            mapped_corporate_authors.append(contributor)

        return self._transform_creatibutors(creators) + mapped_corporate_authors

    def _transform_creatibutors(self, authors):
        """Transform creatibutors."""
        creatibutors = []
        try:
            for author in authors:
                first_name = author.get("first_name")
                last_name = author.get("last_name")
                full_name = author.get("full_name")

                rdm_creatibutor = {
                    "person_or_org": {
                        "type": "personal",
                    }
                }

                if first_name:
                    rdm_creatibutor["person_or_org"]["given_name"] = first_name
                if last_name:
                    rdm_creatibutor["person_or_org"]["family_name"] = last_name
                else:
                    last_name, first_name = full_name.split(", ")
                    rdm_creatibutor["person_or_org"]["family_name"] = last_name
                if first_name and last_name:
                    rdm_creatibutor["person_or_org"]["name"] = (
                        last_name + ", " + first_name
                    )

                creator_affiliations = self._transform_author_affiliations(author)
                creator_identifiers = self._transform_author_identifiers(author)
                role = author.get("inspire_roles")

                if creator_affiliations:
                    rdm_creatibutor["affiliations"] = creator_affiliations

                if creator_identifiers:
                    rdm_creatibutor["person_or_org"][
                        "identifiers"
                    ] = creator_identifiers

                if role:
                    rdm_creatibutor["role"] = role[0]
                creatibutors.append(rdm_creatibutor)
            return creatibutors
        except Exception as e:
            self.metadata_errors.append(
                f"Mapping authors  field failed. INSPIRE#{self.inspire_id}. Error: {e}."
            )
            return None

    def _transform_author_identifiers(self, author):
        """Transform ids of authors. Keeping only ORCID and CDS."""
        author_ids = author.get("ids", [])
        processed_identifiers = []

        schemes_map = {
            "INSPIRE ID": "inspire_author",
            "ORCID": "orcid",
        }

        for author_id in author_ids:
            author_scheme = author_id.get("schema")
            if author_scheme in schemes_map.keys():
                processed_identifiers.append(
                    {
                        "identifier": author_id.get("value"),
                        "scheme": schemes_map[author_scheme],
                    }
                )

        return processed_identifiers

    def _transform_author_affiliations(self, author):
        """Transform affiliations."""
        affiliations = author.get("affiliations", [])
        mapped_affiliations = []

        for affiliation in affiliations:
            value = affiliation.get("value")
            if value:
                mapped_affiliations.append({"name": value})

        return mapped_affiliations

    def _transform_copyrights(self):
        """Transform copyrights."""
        # format: "© {holder} {year}, {statement} {url}"
        copyrights = self.inspire_metadata.get("copyright", [])
        result_list = []

        for cp in copyrights:
            holder = cp.get("holder", "")
            statement = cp.get("statement", "")
            url = cp.get("url", "")
            year = str(cp.get("year", ""))

            if not any([holder, statement, url, year]):
                return None
            else:
                parts = []
                if holder or year:
                    holder_year = " ".join(filter(None, [holder, year]))
                    parts.append(f"{holder_year}")
                if statement or url:
                    statement_url = " ".join(filter(None, [statement, url]))
                    parts.append(statement_url)
                rdm_copyright = "© " + ", ".join(parts)

                result_list.append(rdm_copyright)
        return "<br />".join(result_list)

    def _transform_dois(self):
        """Mapping of record dois."""
        DATACITE_PREFIX = current_app.config["DATACITE_PREFIX"]
        dois = self.inspire_metadata.get("dois", [])

        if not dois:
            return

        seen = set()
        unique_dois = []
        for d in dois:
            if d["value"] not in seen:
                unique_dois.append(d)
                seen.add(d["value"])

        if len(unique_dois) > 1:
            self.metadata_errors.append(
                f"More than 1 DOI was found in INSPIRE#{self.inspire_id}."
            )
            return None
        elif len(unique_dois) == 0:
            return None
        else:
            doi = unique_dois[0].get("value")
            if is_doi(doi):
                mapped_doi = {
                    "identifier": doi,
                }
                if doi.startswith(DATACITE_PREFIX):
                    mapped_doi["provider"] = "datacite"
                else:
                    mapped_doi["provider"] = "external"
                return mapped_doi
            else:
                self.metadata_errors.append(
                    f"DOI validation failed. DOI#{doi}. INSPIRE#{self.inspire_id}."
                )
                return None

    def _transform_identifiers(self):
        identifiers = []
        RDM_RECORDS_IDENTIFIERS_SCHEMES = current_app.config[
            "RDM_RECORDS_IDENTIFIERS_SCHEMES"
        ]
        RDM_RECORDS_RELATED_IDENTIFIERS_SCHEMES = current_app.config[
            "RDM_RECORDS_RELATED_IDENTIFIERS_SCHEMES"
        ]

        external_sys_ids = self.inspire_metadata.get("external_system_identifiers", [])

        for external_sys_id in external_sys_ids:
            schema = external_sys_id.get("schema").lower()
            value = external_sys_id.get("value")
            if schema == "cdsrdm":
                schema = "cds"
            if schema in RDM_RECORDS_IDENTIFIERS_SCHEMES.keys():
                identifiers.append({"identifier": value, "scheme": schema})
            elif schema in RDM_RECORDS_RELATED_IDENTIFIERS_SCHEMES.keys():
                continue
            else:
                self.metadata_errors.append(
                    f"Unexpected schema found in external_system_identifiers. Schema: {schema}, value: {value}. INSPIRE record id: {self.inspire_id}."
                )
        unique_ids = [dict(t) for t in {tuple(sorted(d.items())) for d in identifiers}]
        return unique_ids

    def _transform_related_identifiers(self):
        """Mapping of alternate identifiers."""
        identifiers = []
        RDM_RECORDS_IDENTIFIERS_SCHEMES = current_app.config[
            "RDM_RECORDS_IDENTIFIERS_SCHEMES"
        ]
        RDM_RECORDS_RELATED_IDENTIFIERS_SCHEMES = current_app.config[
            "RDM_RECORDS_RELATED_IDENTIFIERS_SCHEMES"
        ]
        CDS_INSPIRE_IDS_SCHEMES_MAPPING = current_app.config[
            "CDS_INSPIRE_IDS_SCHEMES_MAPPING"
        ]

        try:
            # persistent_identifiers
            persistent_ids = self.inspire_metadata.get("persistent_identifiers", [])
            for persistent_id in persistent_ids:
                schema = persistent_id.get("schema").lower()
                schema = CDS_INSPIRE_IDS_SCHEMES_MAPPING.get(schema, schema)
                value = persistent_id.get("value")
                if schema in RDM_RECORDS_RELATED_IDENTIFIERS_SCHEMES.keys():
                    new_id = {
                        "identifier": value,
                        "scheme": schema,
                        "relation_type": {"id": "isvariantformof"},
                        "resource_type": {"id": "publication-other"},
                    }
                    if schema == "doi":
                        new_id["relation_type"] = {"id": "isversionof"}
                    identifiers.append(new_id)
                elif schema in RDM_RECORDS_IDENTIFIERS_SCHEMES.keys():
                    continue
                else:
                    self.metadata_errors.append(
                        f"Unexpected schema found in persistent_identifiers. Schema: {schema}, value: {value}. INSPIRE#: {self.inspire_id}."
                    )

            # external_system_identifiers
            external_sys_ids = self.inspire_metadata.get(
                "external_system_identifiers", []
            )
            for external_sys_id in external_sys_ids:
                schema = external_sys_id.get("schema").lower()
                value = external_sys_id.get("value")
                if schema in RDM_RECORDS_RELATED_IDENTIFIERS_SCHEMES.keys():
                    new_id = {
                        "identifier": value,
                        "scheme": schema,
                        "relation_type": {"id": "isvariantformof"},
                        "resource_type": {"id": "publication-other"},
                    }
                    if schema == "doi":
                        new_id["relation_type"] = {"id": "isversionof"}
                    identifiers.append(new_id)
                elif schema in RDM_RECORDS_IDENTIFIERS_SCHEMES.keys():
                    continue
                else:
                    self.metadata_errors.append(
                        f"Unexpected schema found in external_system_identifiers. Schema: {schema}, value: {value}. INSPIRE record id: {self.inspire_id}."
                    )

            # ISBNs
            isbns = self.inspire_metadata.get("isbns", [])
            for isbn in isbns:
                value = isbn.get("value")
                _isbn = normalize_isbn(value)
                if not _isbn:
                    self.metadata_errors.append(f"Invalid ISBN '{value}'.")
                else:
                    identifiers.append(
                        {
                            "identifier": _isbn,
                            "scheme": "isbn",
                            "relation_type": {"id": "isvariantformof"},
                            "resource_type": {"id": "publication-book"},
                        }
                    )

            arxiv_ids = self.inspire_metadata.get("arxiv_eprints", [])
            for arxiv_id in arxiv_ids:
                identifiers.append(
                    {
                        "scheme": "arxiv",
                        "identifier": arxiv_id,
                        "relation_type": {"id": "isvariantformof"},
                        "resource_type": {"id": "publication-other"},
                    }
                )

            identifiers.append(
                {
                    "scheme": "inspire",
                    "identifier": self.inspire_id,
                    "relation_type": {"id": "isvariantformof"},
                    "resource_type": {"id": "publication-other"},
                }
            )

            seen = set()
            unique_ids = []
            for d in identifiers:
                s = json.dumps(d, sort_keys=True)
                if s not in seen:
                    seen.add(s)
                    unique_ids.append(d)
            return unique_ids
        except Exception as e:
            self.metadata_errors.append(
                f"Failed mapping identifiers. INSPIRE#: {self.inspire_id}. Error: {e}."
            )
            return None

    def _transform_abstracts(self):
        """Mapping of abstracts."""
        abstracts = self.inspire_metadata.get("abstracts", [])
        if abstracts:
            return abstracts[0]["value"]
        return None

    def _transform_subjects(self):
        """Mapping of keywords to subjects."""
        keywords = self.inspire_metadata.get("keywords", [])
        mapped_subjects = []
        for keyword in keywords:
            value = keyword.get("value")
            if value:
                mapped_subjects.append(
                    {
                        "subject": value,
                    }
                )

        return mapped_subjects

    def _transform_languages(self):
        """Mapping and converting of languages."""
        languages = self.inspire_metadata.get("languages", [])
        mapped_langs = []
        for lang in languages:
            try:
                language = pycountry.languages.get(alpha_2=lang.lower())

                if not language:
                    self.metadata_errors.append(
                        f"Language '{lang}' does not exist. INSPIRE#: {self.inspire_id}."
                    )
                    return
                mapped_langs.append({"id": language.alpha_3})
            except LookupError as e:
                self.metadata_errors.append(
                    f"Failed mapping language '{lang}'. INSPIRE#: {self.inspire_id}. Error: {str(e)}."
                )
                return
        return mapped_langs

    def _transform_additional_descriptions(self):
        """Mapping of additional descriptions."""
        abstracts = self.inspire_metadata.get("abstracts", [])
        additional_descriptions = []

        if len(abstracts) > 1:
            for x in abstracts[1:]:
                additional_descriptions.append(
                    {"description": x["value"], "type": {"id": "abstract"}}
                )

        book_series = self.inspire_metadata.get("book_series", [])
        for book in book_series:
            book_title = book.get("title")
            book_volume = book.get("volume")
            if book_title:
                additional_descriptions.append(
                    {"description": book_title, "type": {"id": "series-information"}}
                )
            if book_volume:
                additional_descriptions.append(
                    {"description": book_volume, "type": {"id": "series-information"}}
                )

        return additional_descriptions

    def _parse_cern_accelerator_experiment(self, value):
        """Parse CERN-<ACCELERATOR>-<EXPERIMENT> format to extract accelerator and experiment."""
        self.logger.debug(f"Parsing CERN accelerator-experiment format: '{value}'")

        if not value or not value.startswith("CERN-"):
            self.logger.debug(
                f"Value '{value}' does not start with CERN- prefix, returning None"
            )
            return None, None

        # Remove CERN- prefix and split on first dash
        parts = value.replace("CERN-", "").strip().split("-", 1)
        accelerator = parts[0] if parts else None
        experiment = parts[1] if len(parts) > 1 else None

        self.logger.debug(
            f"Parsed '{value}' into accelerator='{accelerator}', experiment='{experiment}'"
        )
        return accelerator, experiment

    def _search_vocabulary(self, term, vocab_type):
        """Search vocabulary utility function."""
        self.logger.debug(f"Searching vocabulary '{vocab_type}' for term: '{term}'")

        service = current_service_registry.get("vocabularies")
        if "/" in term:
            # escape the slashes
            term = f'"{term}"'
        try:
            vocabulary_result = service.search(
                system_identity, type=vocab_type, q=f'id:"{term}"'
            ).to_dict()
            hits = vocabulary_result.get("hits", {}).get("total", 0)
            self.logger.debug(
                f"Vocabulary search returned {hits} results for '{term}' in '{vocab_type}'"
            )
            return vocabulary_result
        except RequestError as e:
            self.logger.error(
                f"Failed vocabulary search ['{term}'] in '{vocab_type}'. INSPIRE#: {self.inspire_id}. Error: {e}."
            )
        except NoResultFound as e:
            self.logger.error(
                f"Vocabulary term ['{term}'] not found in '{vocab_type}'. INSPIRE#: {self.inspire_id}"
            )
            raise e

    def _transform_accelerators(self, inspire_accelerators):
        """Map accelerators to CDS-RDM vocabulary."""
        inspire_id = self.inspire_metadata.get("control_number")
        self.logger.debug(
            f"Mapping {len(inspire_accelerators)} accelerators: {inspire_accelerators}"
        )

        mapped = []
        for accelerator in inspire_accelerators:

            if accelerator.startswith("CERN-"):
                # First try the full string without CERN- prefix
                full_string = accelerator.replace("CERN-", "").strip()
                self.logger.debug(
                    f"CERN accelerator detected, trying full string '{full_string}' first"
                )
                result = self._search_vocabulary(full_string, "accelerators")

                if result and result.get("hits", {}).get("total"):
                    # Found the full string as an accelerator
                    self.logger.info(f"Found accelerator '{full_string}'")
                    mapped.append({"id": result["hits"]["hits"][0]["id"]})
                    continue

                # If not found, try parsing as CERN-<ACCELERATOR>-<EXPERIMENT>
                self.logger.debug(
                    f"Term '{full_string}' not found, parse as combined format"
                )
                parsed_acc, _ = self._parse_cern_accelerator_experiment(accelerator)
                accelerator_to_search = parsed_acc if parsed_acc else full_string

                self.logger.debug(
                    f"Searching for accelerator: '{accelerator_to_search}'"
                )

                result = self._search_vocabulary(accelerator_to_search, "accelerators")
                if result and result.get("hits", {}).get("total"):
                    self.logger.info(
                        f"Mapped accelerator '{accelerator_to_search}' from '{accelerator}'"
                    )
                    mapped.append({"id": result["hits"]["hits"][0]["id"]})
                else:
                    self.logger.error(
                        f"Failed to map accelerator '{accelerator_to_search}'. INSPIRE#: {self.inspire_id}."
                    )
                    return
            else:
                # Handle non-CERN accelerators
                self.logger.debug(f"Processing non-CERN accelerator: '{accelerator}'")
                result = self._search_vocabulary(accelerator, "accelerators")
                if result and result.get("hits", {}).get("total"):
                    self.logger.info(f"Mapped non-CERN accelerator: '{accelerator}'")
                    mapped.append({"id": result["hits"]["hits"][0]["id"]})
                else:
                    self.logger.error(
                        f"Failed to map accelerator '{accelerator}'. INSPIRE#: {self.inspire_id}."
                    )
                    return

        self.logger.debug(
            f"Accelerator transformation completed, mapped {len(mapped)} accelerators"
        )
        return mapped

    def _transform_experiments(self, inspire_experiments):
        """Map experiments to CDS-RDM vocabulary."""
        self.logger.debug(
            f"Start experiment transformation with {len(inspire_experiments)} experiments: {inspire_experiments}"
        )

        mapped = []
        for experiment in inspire_experiments:
            self.logger.debug(f"Processing experiment: '{experiment}'")

            if experiment.startswith("CERN-"):
                # First try the full string without CERN- prefix
                full_string = experiment.replace("CERN-", "").strip()
                self.logger.debug(
                    f"CERN experiment detected, trying full string '{full_string}' first"
                )
                result = self._search_vocabulary(full_string, "experiments")

                if result and result.get("hits", {}).get("total"):
                    # Found the full string as an experiment
                    self.logger.info(
                        f"Found experiment '{full_string}' as full match in vocabulary"
                    )
                    mapped.append({"id": result["hits"]["hits"][0]["id"]})
                    continue

                # If not found, try parsing as CERN-<ACCELERATOR>-<EXPERIMENT>
                self.logger.debug(
                    f"Full string '{full_string}' not found, attempting to parse as combined format"
                )
                _, parsed_exp = self._parse_cern_accelerator_experiment(experiment)
                experiment_to_search = parsed_exp if parsed_exp else full_string

                self.logger.debug(
                    f"Search for experiment component: '{experiment_to_search}'"
                )

                result = self._search_vocabulary(experiment_to_search, "experiments")
                if result and result.get("hits", {}).get("total"):
                    self.logger.info(
                        f"Successfully mapped experiment '{experiment_to_search}' from '{experiment}'"
                    )
                    mapped.append({"id": result["hits"]["hits"][0]["id"]})
                else:
                    self.logger.error(
                        f"Failed to map experiment '{experiment_to_search}'. INSPIRE#: {self.inspire_id}."
                    )
                    return
            else:
                # Handle non-CERN experiments
                self.logger.debug(f"Process non-CERN experiment: '{experiment}'")
                result = self._search_vocabulary(experiment, "experiments")
                if result and result.get("hits", {}).get("total"):
                    self.logger.info(
                        f"Successfully mapped non-CERN experiment: '{experiment}'"
                    )
                    mapped.append({"id": result["hits"]["hits"][0]["id"]})
                else:
                    self.logger.error(
                        f"Failed to map experiment '{experiment}'. INSPIRE#: {self.inspire_id}."
                    )
                    return

        self.logger.debug(
            f"Experiment transformation completed, mapped {len(mapped)} experiments"
        )
        return mapped

    def _transform_thesis(self, thesis_info):
        """Transform thesis information to custom field format."""
        defense_date = thesis_info.get("defense_date")
        return {
            "date_defended": defense_date,
        }

    def _transform_custom_fields(self):
        """Mapping of custom fields."""
        custom_fields = {}
        # TODO parse legacy name or check with Micha if they can expose name
        inspire_accelerators = []
        inspire_experiments = []

        # Extract accelerators and experiments, handling combined formats
        for x in self.inspire_metadata.get("accelerator_experiments", []):
            accelerator_value = x.get("accelerator")
            experiment_value = x.get("legacy_name")

            # Handle accelerator field
            if accelerator_value:
                inspire_accelerators.append(accelerator_value)

            # Handle experiment field
            if experiment_value:
                inspire_experiments.append(experiment_value)

        thesis_info = self.inspire_metadata.get("thesis_info", {})
        defense_date = thesis_info.get("defense_date")
        if defense_date:
            custom_fields["thesis:thesis"] = self._transform_thesis(thesis_info)

        imprint = self._validate_imprint()

        # Map accelerator and experiment vocabularies
        if mapped_accelerators := self._transform_accelerators(inspire_accelerators):
            custom_fields["cern:accelerators"] = mapped_accelerators

        if mapped_experiments := self._transform_experiments(inspire_experiments):
            custom_fields["cern:experiments"] = mapped_experiments

        # Map imprint place
        if imprint_place := imprint.get("place") if imprint else None:
            custom_fields["imprint:imprint"] = {"place": imprint_place}

        imprint_fields = custom_fields.get("imprint:imprint", {})

        isbns = self.inspire_metadata.get("isbns", [])
        online_isbns = []
        for isbn in isbns:
            value = isbn.get("value")
            valid_isbn = normalize_isbn(value)
            if not valid_isbn:
                self.metadata_errors.append(f"Invalid ISBN '{value}'.")
            else:
                if isbn.get("medium") == "online":
                    online_isbns.append(valid_isbn)

        if len(online_isbns) > 1:
            self.metadata_errors.append(
                f"More than one electronic ISBN found: {online_isbns}."
            )
        elif len(online_isbns) == 1:
            imprint_fields["isbn"] = online_isbns[0]

        if imprint_fields:
            custom_fields["imprint:imprint"] = imprint_fields
        return custom_fields

    def transform_metadata(self):
        """Transform INSPIRE metadata."""
        self.logger.debug(f"Start transform_metadata")

        title, additional_titles = self._transform_titles()

        rdm_metadata = {
            "creators": self._transform_creators(),
            "contributor": self._transform_contributors(),
            "identifiers": self._transform_identifiers(),
            "related_identifiers": self._transform_related_identifiers(),
            "publication_date": self._transform_publication_date(),
            "languages": self._transform_languages(),
            "publisher": self._transform_publisher(),
            "title": title,
            "additional_titles": additional_titles,
            "copyright": self._transform_copyrights(),
            "description": self._transform_abstracts(),
            "additional_descriptions": self._transform_additional_descriptions(),
            "subjects": self._transform_subjects(),
            "resource_type": self._transform_document_type(),
        }

        result = {k: v for k, v in rdm_metadata.items() if v}
        self.logger.debug(
            f"Metadata transformation completed with {len(result)} fields"
        )

        return result

    def transform_pids(self):
        """Transform INSPIRE pids."""
        doi = self._transform_dois()
        if doi:
            pids = {
                "doi": doi,
            }
            return pids
        else:
            return None

    def transform_record(self):
        """Perform record transformation."""
        self.logger.debug("Start transform_record")

        metadata = self.transform_metadata()

        self.logger.debug("Transforming custom fields")
        custom_fields = self._transform_custom_fields()

        record = {
            "metadata": metadata,
            "custom_fields": custom_fields,
        }
        self.logger.debug("Transforming PIDs")
        pids = self.transform_pids()

        if pids:
            record["pids"] = pids
            self.logger.debug(f"PIDs added to record")

        self.logger.debug(
            f"Record transformation completed with {len(self.metadata_errors)} errors"
        )
        return record, self.metadata_errors

    def _transform_files(self):
        """Mapping of INSPIRE documents to files."""
        self.logger.debug(f"Starting _transform_files")

        rdm_files_entries = {}
        inspire_files = self.inspire_metadata.get("documents", [])
        self.logger.debug(f" Processing {len(inspire_files)} documents")

        for file in inspire_files:
            self.logger.debug(f"Processing file: {file.get('filename', 'unknown')}")
            filename = file["filename"]
            if "pdf" not in filename:
                # INSPIRE only exposes pdfs for us
                filename = f"{filename}.pdf"
            try:
                file_details = {
                    "checksum": f"md5:{file['key']}",
                    "key": filename,
                    "access": {"hidden": False},
                    "inspire_url": file["url"],  # put this somewhere else
                }

                rdm_files_entries[filename] = file_details
                self.logger.info(f"File mapped: {file_details}. File name: {filename}.")

                file_metadata = {}
                file_description = file.get("description")
                file_original_url = file.get("original_url")
                if file_description:
                    file_metadata["description"] = file_description
                if file_original_url:
                    file_metadata["original_url"] = file_original_url

                if file_metadata:
                    rdm_files_entries[filename]["metadata"] = file_metadata

            except Exception as e:
                self.files_errors.append(
                    f"Error occurred while mapping files. File key: {file['key']}. INSPIRE record id: {self.inspire_id}. Error: {e}."
                )

        return {
            "enabled": True,
            "entries": rdm_files_entries,
        }

    def transform_files(self):
        """Transform INSPIRE documents and figures."""
        self.logger.debug("Starting transform_files")

        transformed_files = self._transform_files()
        self.logger.debug(
            f"Files transformation completed with {len(self.files_errors)} errors"
        )
        return transformed_files, self.files_errors
