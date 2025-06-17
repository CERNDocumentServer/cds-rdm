# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Transform RDM entry."""
import pycountry
from babel_edtf import parse_edtf
from edtf.parser.grammar import ParseException
from flask import current_app
from idutils import detect_identifier_schemes
from idutils.normalizers import normalize_isbn
from idutils.validators import is_doi, is_url
from invenio_access.permissions import system_identity, system_user_id
from invenio_records_resources.proxies import current_service_registry
from opensearchpy import RequestError
from sqlalchemy.orm.exc import NoResultFound


class RDMEntry:
    """Building of CDS-RDM entry record."""

    def __init__(self, inspire_record):
        """Initializes the RDM entry."""
        self.inspire_record = inspire_record
        self.inspire_metadata = inspire_record["metadata"]
        self.transformer = Inspire2RDM(self.inspire_metadata, self.inspire_record)
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
        inspire_files = self.inspire_metadata.get("documents", [])

        if not inspire_files:
            self.errors.append(
                f"INSPIRE record #{self.inspire_metadata['control_number']} has no files. Metadata-only records are not supported. Aborting record transformation."
            )
            return None, self.errors

        record = self._record()
        rdm_record = {
            "id": self._id(),
            "metadata": record["metadata"],
            "custom_fields": record["custom_fields"],
            "files": self._files(),
            "parent": self._parent(),
            "access": self._access(),
        }

        if record.get("pids"):
            rdm_record["pids"] = record["pids"]

        current_app.logger.debug(
            f"Building CDS-RDM entry record finished. RDM record: {rdm_record}."
        )
        return rdm_record, self.errors


class Inspire2RDM:
    """INSPIRE to CDS-RDM record mapping."""

    def __init__(self, inspire_metadata, inspire_record):
        """Initializes the Inspire2RDM class."""
        self.inspire_metadata = inspire_metadata
        self.inspire_record = inspire_record
        self.metadata_errors = []
        self.files_errors = []

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
                    f"Error occurred while mapping titles. Title from INSPIRE: {inspire_title}. INSPIRE record id: {self.inspire_metadata.get('control_number')}. Error: {e}."
                )
                return None, None

        translations = self.inspire_metadata.get("title_translations", [])
        for translation in translations:
            lang = translation.get("language")
            title = translation.get("title")
            subtitle = translation.get("subtitle")
            if title:
                trans_title = {"title": title, "type": {"id": "translated-title"}}
                if lang:
                    trans_title["lang"] = lang
                rdm_additional_titles.append(trans_title)
            if subtitle:
                sub = {"title": subtitle, "type": {"id": "subtitle"}}
                if lang:
                    sub["lang"] = lang
                rdm_additional_titles.append(sub)

        return rdm_title, rdm_additional_titles

    def _validate_imprint(self):
        """Validate that record has only 1 imprint."""
        imprints = self.inspire_metadata.get("imprints", [])

        if not imprints:
            return
        if len(imprints) > 1:
            self.metadata_errors.append(
                f"More than 1 imprint found. INSPIRE record id: {self.inspire_metadata.get('control_number')}."
            )
            return

        return imprints[0]

    def _transform_publisher(self):
        """Mapping of publisher."""
        imprint = self._validate_imprint()
        if not imprint:
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
                f"Couldn't get publication date. INSPIRE record id: {self.inspire_metadata.get('control_number')}."
            )
            return None
        try:
            parsed_date = str(parse_edtf(thesis_date))
            return parsed_date
        except ParseException as e:
            self.metadata_errors.append(
                f"Error occurred while parsing imprint.date to EDTF level 0 format for publication_date. "
                f"INSPIRE record id: {self.inspire_metadata['control_number']}. Date: {thesis_date}. "
                f"Error: {e}."
            )
            return None

    def _transform_document_type(self):
        """Mapping of INSPIRE document type to resource type."""
        # document_type = self.inspire_metadata.get("document_type")[0]
        #
        # document_type_mapping = {
        #     "activity report": "publication-report",
        #     "article": "publication-article",
        #     "book": "publication-book",
        #     "book chapter": "publication-section",
        #     "conference paper": "publication-conferencepaper",
        #     "note": "publication-technicalnote",
        #     "proceedings": "publication-conferenceproceeding",
        #     "report": "publication-report",
        #     "thesis": "publication-thesis",
        # }
        #
        # if document_type not in document_type_mapping:
        #     self.metadata_errors.append(
        #         f"Error occurred while mapping document_type to resource_type. Couldn't fine a mapping rule for "
        #         f"document_type {document_type}. INSPIRE record id: {self.inspire_metadata.get('control_number')}."
        #     )
        #     return None

        # return document_type_mapping.get(document_type)

        document_types = self.inspire_metadata.get("document_type", [])
        for doc_type in document_types:
            if doc_type != "thesis":
                self.metadata_errors.append(
                    f"Only thesis are supported for now.{doc_type} not supported."
                )
                return None

        # uncomment the part above for other doc types (thesis have only 1 possible doc type)
        return {"id": "publication-thesis"}

    def _transform_contributors(self):
        """Mapping of INSPIRE authors to contributors."""
        authors = self.inspire_metadata.get("authors", [])
        contributors = []

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

        collaborations = self.inspire_metadata.get("collaboration", [])
        for collab in collaborations:
            name = collab.get("value") if isinstance(collab, dict) else collab
            if name:
                mapped_corporate_authors.append(
                    {"person_or_org": {"type": "organizational", "name": name}}
                )

        record_affiliations = self.inspire_metadata.get("record_affiliations", [])
        for rec_aff in record_affiliations:
            rec = rec_aff.get("record") if isinstance(rec_aff, dict) else rec_aff
            if rec:
                mapped_corporate_authors.append(
                    {
                        "person_or_org": {"type": "organizational", "name": rec},
                        # TODO: map to ROR identifier when available
                    }
                )

        for author in authors:
            inspire_roles = author.get("inspire_roles", [])
            if "supervisor" in inspire_roles:
                contributors.append(author)

        return self._transform_creatibutors(contributors) + mapped_corporate_authors

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

        return self._transform_creatibutors(creators)

    def _transform_creatibutors(self, authors):
        """Transform creatibutors."""
        creatibutors = []
        try:
            for author in authors:
                first_name = author.get("first_name")
                last_name = author.get("last_name")

                # If both first_name and last_name are missing, try to parse from full_name
                if not first_name and not last_name:
                    full_name = author.get("full_name")
                    if full_name:
                        if "," in full_name:
                            parts = [part.strip() for part in full_name.split(",", 1)]
                            if len(parts) == 2:
                                last_name, first_name = parts
                        else:
                            last_name = full_name.strip()

                rdm_creatibutor = {
                    "person_or_org": {
                        "type": "personal",
                    }
                }

                if first_name:
                    rdm_creatibutor["person_or_org"]["given_name"] = first_name
                if last_name:
                    rdm_creatibutor["person_or_org"]["family_name"] = last_name
                if first_name and last_name:
                    rdm_creatibutor["person_or_org"][
                        "name"
                    ] = f"{last_name}, {first_name}"

                creator_affiliations = self._transform_author_affiliations(author)
                creator_identifiers = self._transform_author_identifiers(author)
                role = author.get("inspire_roles")

                if creator_affiliations:
                    rdm_creatibutor["affiliations"] = creator_affiliations

                if creator_identifiers:
                    rdm_creatibutor["person_or_org"][
                        "identifiers"
                    ] = creator_identifiers

                if role and role not in ["author"]:  # author is not a valid role
                    rdm_creatibutor["role"] = {"id": role[0]}
                creatibutors.append(rdm_creatibutor)
            return creatibutors
        except Exception as e:
            self.metadata_errors.append(
                f"Error occurred while mapping INSPIRE authors to creators and contributors. INSPIRE "
                f"record id: {self.inspire_metadata.get('control_number')}. Error: {e}."
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
                continue  # Skip empty entries

            parts = []
            if holder or year:
                holder_year = " ".join(filter(None, [holder, year]))
                parts.append(holder_year)
            if statement or url:
                statement_url = " ".join(filter(None, [statement, url]))
                parts.append(statement_url)
            rdm_copyright = "© " + ", ".join(parts)

            result_list.append(rdm_copyright)

        return "<br />".join(result_list) if result_list else None

    def _transform_rights(self):
        """Transform license information to rights."""
        licenses = self.inspire_metadata.get("license", [])
        rights = []
        for lic in licenses:
            right = {}
            imposing = lic.get("imposing")
            license_id = lic.get("license")
            url = lic.get("url")
            if imposing:
                right["description"] = imposing
            if license_id:
                result = self._search_vocabulary(license_id.lower(), "licenses")
                if result and result.get("hits", {}).get("total", 0) > 0:
                    right["id"] = result["hits"]["hits"][0]["id"]
                else:
                    right["title"] = {"en": license_id}
            if url:
                right["link"] = url
            if right:
                rights.append(right)
        return rights

    def _transform_dois(self):
        """Mapping of record dois."""
        DATACITE_PREFIX = current_app.config["DATACITE_PREFIX"]
        dois = self.inspire_metadata.get("dois", [])

        if len(dois) > 1:
            self.metadata_errors.append(
                f"More than 1 DOI was found in the INSPIRE record #{self.inspire_metadata.get('control_number')}."
            )
            return None
        elif len(dois) == 0:
            return None
        else:
            doi = dois[0].get("value")
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
                    f"DOI validation failed. Value: {doi}. INSPIRE record #{self.inspire_metadata.get('control_number')}."
                )
                return None

    def _transform_alternate_identifiers(self):
        """Mapping of alternate identifiers."""
        identifiers = []
        inspire_id = self.inspire_metadata.get("control_number")
        RDM_RECORDS_IDENTIFIERS_SCHEMES = current_app.config[
            "RDM_RECORDS_IDENTIFIERS_SCHEMES"
        ]
        IDENTIFIERS_SCHEMES_TO_DROP = ["SPIRES", "HAL", "OSTI", "SLAC", "PROQUEST"]

        try:
            # persistent_identifiers
            persistent_ids = self.inspire_metadata.get("persistent_identifiers", [])
            for persistent_id in persistent_ids:
                schema = persistent_id.get("schema").lower()
                value = persistent_id.get("value")
                if schema.upper() in IDENTIFIERS_SCHEMES_TO_DROP:
                    continue
                if schema not in RDM_RECORDS_IDENTIFIERS_SCHEMES.keys():
                    self.metadata_errors.append(
                        f"Unexpected schema found in persistent_identifiers. Schema: {schema}, value: {value}. INSPIRE record id: {inspire_id}."
                    )
                else:
                    identifiers.append({"identifier": value, "scheme": schema})

            # add INSPIRE id
            identifiers.append({"identifier": str(inspire_id), "scheme": "inspire"})

            # external_system_identifiers
            external_sys_ids = self.inspire_metadata.get(
                "external_system_identifiers", []
            )
            for external_sys_id in external_sys_ids:
                schema = external_sys_id.get("schema").lower()
                if schema == "cds":
                    schema = "lcds"
                value = external_sys_id.get("value")
                if schema.upper() in IDENTIFIERS_SCHEMES_TO_DROP:
                    continue
                if schema not in RDM_RECORDS_IDENTIFIERS_SCHEMES.keys():
                    self.metadata_errors.append(
                        f"Unexpected schema found in external_system_identifiers. Schema: {schema}, value: {value}. INSPIRE record id: {inspire_id}."
                    )
                else:
                    identifiers.append({"identifier": value, "scheme": schema})

            # ISBNs
            isbns = self.inspire_metadata.get("isbns", [])
            for isbn in isbns:
                value = isbn.get("value")
                _isbn = normalize_isbn(value)
                if not _isbn:
                    self.metadata_errors.append(f"Invalid ISBN '{value}'.")
                else:
                    identifiers.append({"identifier": _isbn, "scheme": "isbn"})

            urls = self.inspire_metadata.get("urls", [])
            for url in urls:
                val = url.get("value")
                if val and is_url(val):
                    identifiers.append({"identifier": val, "scheme": "url"})

            return identifiers
        except Exception as e:
            self.metadata_errors.append(
                f"Error occurred while mapping alternate identifiers. INSPIRE record id: {inspire_id}. Error: {e}."
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
            schema = keyword.get("schema", "").upper()

            if not value:
                continue

            if schema in ["PACS", "CERN LIBRARY"]:
                continue

            if schema in ["CERN", "CDS"]:
                result = self._search_vocabulary(value, "subjects")
                if result and result.get("hits", {}).get("total", 0) > 0:
                    subject_id = result["hits"]["hits"][0]["id"]
                    mapped_subjects.append({"id": subject_id})
                else:
                    mapped_subjects.append({"subject": value})
            else:
                mapped_subjects.append({"subject": value})

        return mapped_subjects

    def _transform_languages(self):
        """Mapping and converting of languages."""
        languages = self.inspire_metadata.get("languages", [])
        mapped_langs = []
        for lang in languages:
            try:
                mapped_langs.append(
                    {"id": pycountry.languages.get(alpha_2=lang.lower()).alpha_3}
                )
            except (KeyError, AttributeError, LookupError) as e:
                self.metadata_errors.append(
                    f"Error occurred while mapping language '{lang}'. INSPIRE record id: {self.inspire_metadata.get('control_number')}. Error: {str(e)}."
                )
                return None
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

        public_notes = self.inspire_metadata.get("public_notes", [])
        for note in public_notes:
            value = note.get("value")
            if value:
                additional_descriptions.append(
                    {"description": value, "type": {"id": "other"}}
                )

        return additional_descriptions

    def _transform_related_identifiers(self):
        """Map related identifiers from INSPIRE record."""
        related_identifiers = []

        relation_map = {
            "predecessor": "continues",
            "successor": "is continued by",
            "parent": "is part of",
            "commented": "reviews",
        }

        related_records = self.inspire_metadata.get("related_records", [])
        for rel in related_records:
            identifier = rel.get("record")
            if not identifier:
                continue
            scheme = "url" if is_url(identifier) else None
            if not scheme:
                detected = detect_identifier_schemes(identifier)
                if detected:
                    scheme = detected[0].lower()
            if not scheme:
                self.metadata_errors.append(
                    f"Could not detect scheme for related identifier '{identifier}'."
                )
                continue
            relation = relation_map.get(rel.get("relation"))
            if not relation:
                self.metadata_errors.append(
                    f"Unknown relation type '{rel.get('relation')}' for identifier '{identifier}'."
                )
                continue
            related_identifiers.append(
                {
                    "identifier": identifier,
                    "scheme": scheme,
                    "relation_type": {"id": relation},
                }
            )

        pub_infos = self.inspire_metadata.get("publication_info", [])
        for info in pub_infos:
            if journal_record := info.get("journal_record"):
                related_identifiers.append(
                    {
                        "identifier": journal_record,
                        "scheme": "url",
                        "relation_type": {"id": "published_in"},
                    }
                )
            if parent_isbn := info.get("parent_isbn"):
                isbn = normalize_isbn(parent_isbn)
                if isbn:
                    related_identifiers.append(
                        {
                            "identifier": isbn,
                            "scheme": "isbn",
                            "relation_type": {"id": "published_in"},
                        }
                    )
            if parent_record := info.get("parent_record"):
                related_identifiers.append(
                    {
                        "identifier": parent_record,
                        "scheme": "url",
                        "relation_type": {"id": "published_in"},
                    }
                )
            if parent_rep := info.get("parent_report_number"):
                related_identifiers.append(
                    {
                        "identifier": parent_rep,
                        "scheme": "cdsref",
                        "relation_type": {"id": "published_in"},
                    }
                )

        return related_identifiers

    def _search_vocabulary(self, term, vocab_type):
        """Search vocabulary utility function."""
        service = current_service_registry.get("vocabularies")
        if "/" in term:
            # escape the slashes
            term = f'"{term}"'
        try:
            vocabulary_result = service.search(
                system_identity, type=vocab_type, q=f'id:"{term}"'
            ).to_dict()
            return vocabulary_result
        except RequestError as e:
            current_app.logger.warning(
                f"Error occurred when searching for '{term}' in the vocabulary '{vocab_type}'. INSPIRE record id: {self.inspire_metadata.get('control_number')}. Error: {e}."
            )
        except NoResultFound as e:
            current_app.logger.warning(
                f"No result found when searching for '{term}' in the vocabulary '{vocab_type}'. INSPIRE record id: {self.inspire_metadata.get('control_number')}. Error: {e}."
            )

    def _transform_accelerators(self, inspire_accelerators):
        """Map accelerators to CDS-RDM vocabulary."""
        mapped = []
        for accelerator in inspire_accelerators:
            result = self._search_vocabulary(accelerator, "accelerators")
            if result.get("hits", {}).get("total"):
                mapped.append({"id": result["hits"]["hits"][0]["id"]})
            else:
                self.metadata_errors.append(
                    f"Couldn't map accelerator '{accelerator}' value to anything in existing vocabulary. INSPIRE record id: {self.inspire_metadata.get('control_number')}."
                )
                return
        return mapped

    def _transform_experiments(self, inspire_experiments):
        """Map experiments to CDS-RDM vocabulary."""
        mapped = []
        for experiment in inspire_experiments:
            result = self._search_vocabulary(experiment, "experiments")
            if result.get("hits", {}).get("total"):
                mapped.append({"id": result["hits"]["hits"][0]["id"]})
            else:
                self.metadata_errors.append(
                    f"Couldn't map experiment '{experiment}' value to anything in existing vocabulary. INSPIRE record id: {self.inspire_metadata.get('control_number')}."
                )
                return
        return mapped

    def _transform_thesis(self, thesis_info):
        """Transform thesis information to custom field format."""
        result = {}
        submission_date = thesis_info.get("date")
        defense_date = thesis_info.get("defense_date")
        degree_type = thesis_info.get("degree_type")
        institutions = thesis_info.get("institutions", [])

        if submission_date:
            result["date_submitted"] = submission_date
        if defense_date:
            result["date_defended"] = defense_date
        if degree_type:
            result["type"] = degree_type
        if institutions:
            uni = institutions[0].get("name")
            if uni:
                result["university"] = uni
        return result

    def _transform_journal(self, info):
        """Transform journal publication info."""
        journal = {}
        if title := info.get("journal_title"):
            journal["title"] = title
        if volume := info.get("journal_volume"):
            journal["volume"] = volume
        if issue := info.get("journal_issue"):
            journal["issue"] = issue
        page_start = info.get("page_start")
        page_end = info.get("page_end")
        page_range = None
        if page_start and page_end:
            page_range = f"{page_start}-{page_end}"
        elif page_start:
            page_range = page_start
        elif page_end:
            page_range = page_end
        artid = info.get("artid")
        pages_val = None
        if page_range:
            journal["page_range"] = page_range
            if artid:
                pages_val = f"{page_range}, {artid}"
        elif artid:
            pages_val = artid
        if pages_val:
            journal["pages"] = pages_val
        return journal

    def _transform_meeting(self, info):
        """Transform meeting information."""
        meeting = {}
        if acronym := info.get("conf_acronym"):
            meeting["acronym"] = acronym
        identifiers = []
        cnum = info.get("cnum")
        conf_record = info.get("conference_record")
        if cnum:
            identifiers.append({"scheme": "inspire", "value": cnum})
        if conf_record:
            identifiers.append({"scheme": "url", "value": conf_record})
        if identifiers:
            meeting["identifiers"] = identifiers
        return meeting

    def transform_custom_fields(self):
        """Mapping of custom fields."""
        custom_fields = {}
        # TODO parse legacy name or check with Micha if they can expose name
        inspire_accelerators = [
            x.get("accelerator")
            for x in self.inspire_metadata.get("accelerator_experiments", [])
            if x.get("accelerator")
        ]
        inspire_experiments = [
            x.get("legacy_name")
            for x in self.inspire_metadata.get("accelerator_experiments", [])
            if x.get("legacy_name")
        ]

        thesis_info = self.inspire_metadata.get("thesis_info", {})
        if thesis_info:
            thesis_cf = self._transform_thesis(thesis_info)
            if thesis_cf:
                custom_fields["thesis:thesis"] = thesis_cf

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

        pub_infos = self.inspire_metadata.get("publication_info", [])
        if pub_infos:
            journal_cf = self._transform_journal(pub_infos[0])
            if journal_cf:
                custom_fields["journal:journal"] = journal_cf

            meeting_cf = self._transform_meeting(pub_infos[0])
            if meeting_cf:
                custom_fields["meeting:meeting"] = meeting_cf
        return custom_fields

    def transform_metadata(self):
        """Transform INSPIRE metadata."""
        title, additional_titles = self._transform_titles()

        rdm_metadata = {
            "creators": self._transform_creators(),
            "contributor": self._transform_contributors(),
            "identifiers": self._transform_alternate_identifiers(),
            "additional_descriptions": self._transform_additional_descriptions(),
            "publication_date": self._transform_publication_date(),
            "languages": self._transform_languages(),
            "publisher": self._transform_publisher(),
            "title": title,
            "additional_titles": additional_titles,
            "copyright": self._transform_copyrights(),
            "rights": self._transform_rights(),
            "description": self._transform_abstracts(),
            "additional_descriptions": self._transform_additional_descriptions(),
            "subjects": self._transform_subjects(),
            "resource_type": self._transform_document_type(),
            "related_identifiers": self._transform_related_identifiers(),
        }

        result = {k: v for k, v in rdm_metadata.items() if v}

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
        record = {
            "metadata": self.transform_metadata(),
            "custom_fields": self.transform_custom_fields(),
        }
        pids = self.transform_pids()
        if pids:
            record["pids"] = pids

        return record, self.metadata_errors

    def _transform_files(self):
        """Mapping of INSPIRE documents to files."""
        rdm_files_entries = {}
        inspire_files = self.inspire_metadata.get("documents", [])

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

                file_metadata = {}
                file_description = file.get("description")
                file_original_url = file.get("original_url")
                if file_description:
                    file_metadata["description"] = file_description
                if file_original_url:
                    file_metadata["original_url"] = file_original_url

                if file_metadata:
                    rdm_files_entries[file["filename"]]["metadata"] = file_metadata

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
