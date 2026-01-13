# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the GPL-2.0 License; see LICENSE file for more details.

"""INSPIRE to CDS harvester module."""

from dataclasses import dataclass

import pycountry
from babel_edtf import parse_edtf
from edtf.parser.grammar import ParseException
from flask import current_app

from cds_rdm.inspire_harvester.transform.mappers.mapper import MapperBase


@dataclass(frozen=True)
class ResourceTypeMapper(MapperBase):
    id = "metadata.resource_type.id"

    def map_value(self, src_metadata, ctx, logger):

        return ctx.resource_type.value


@dataclass(frozen=True)
class TitleMapper(MapperBase):
    id = "metadata.title"

    def map_value(self, src_metadata, ctx, logger):
        inspire_titles = src_metadata.get("titles", [])
        return inspire_titles[0].get("title")


@dataclass(frozen=True)
class AdditionalTitlesMapper(MapperBase):
    id = "metadata.additional_titles"

    def map_value(self, src_metadata, ctx, logger):
        inspire_titles = src_metadata.get("titles", [])
        rdm_additional_titles = []
        for i, inspire_title in enumerate(inspire_titles[1:]):
            try:

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
                ctx.errors.append(
                    f"Title {inspire_title} transform failed. INSPIRE#{ctx.inspire_id}. Error: {e}."
                )
        return rdm_additional_titles


@dataclass(frozen=True)
class PublisherMapper(MapperBase):
    id = "metadata.publisher"

    def validate(self, src, ctx):
        imprints = src.get("imprints", [])

        if len(imprints) > 1:
            ctx.errors.append(f"More than 1 imprint found. INSPIRE#{ctx.inspire_id}.")

    def map_value(self, src_metadata, ctx, logger):
        imprints = src_metadata.get("imprints", [])
        imprint = None
        publisher = None
        if imprints:
            imprint = imprints[0]
            publisher = imprint.get("publisher")

        DATACITE_PREFIX = current_app.config["DATACITE_PREFIX"]
        dois = src_metadata.get("dois", [])

        has_cds_doi = next(
            (d["value"] for d in dois if d["value"].startswith(DATACITE_PREFIX)),
            False,
        )
        if has_cds_doi and not publisher:
            return "CERN"
        return publisher


@dataclass(frozen=True)
class PublicationDateMapper(MapperBase):

    id = "metadata.publication_date"

    def map_value(self, src_metadata, ctx, logger):
        """Transform publication date."""
        imprints = src_metadata.get("imprints", [])
        imprint_date = imprints[0].get("date") if imprints else None

        publication_info = src_metadata.get("publication_info", [])
        publication_date = publication_info[0].get("year") if publication_info else None

        creation_date = src_metadata.get("created")

        date = publication_date or imprint_date or creation_date
        if date and isinstance(date, int):
            date = str(date)
        try:
            parsed_date = str(parse_edtf(date))
            return parsed_date
        except ParseException as e:
            ctx.errors.append(
                f"Publication date transformation failed."
                f"INSPIRE#{ctx.inspire_id}. Date: {date}. "
                f"Error: {e}."
            )


@dataclass(frozen=True)
class CopyrightMapper(MapperBase):

    id = "metadata.copyright"

    def map_value(self, src_metadata, ctx, logger):
        """Transform copyrights."""
        # format: "© {holder} {year}, {statement} {url}"
        copyrights = src_metadata.get("copyright", [])
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


@dataclass(frozen=True)
class DescriptionMapper(MapperBase):

    id = "metadata.description"

    def map_value(self, src_metadata, ctx, logger):
        """Mapping of abstracts."""
        abstracts = src_metadata.get("abstracts", [])
        if abstracts:
            return abstracts[0]["value"]


@dataclass(frozen=True)
class AdditionalDescriptionsMapper(MapperBase):
    id = "metadata.additional_descriptions"

    def map_value(self, src_metadata, ctx, logger):
        """Mapping of additional descriptions."""
        abstracts = src_metadata.get("abstracts", [])
        additional_descriptions = []

        if len(abstracts) > 1:
            for x in abstracts[1:]:
                additional_descriptions.append(
                    {"description": x["value"], "type": {"id": "abstract"}}
                )

        # TODO move it to book resource?
        book_series = src_metadata.get("book_series", [])
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


@dataclass(frozen=True)
class SubjectsMapper(MapperBase):
    id = "metadata.subjects"

    def map_value(self, src_metadata, ctx, logger):
        """Mapping of keywords to subjects."""
        keywords = src_metadata.get("keywords", [])
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


@dataclass(frozen=True)
class LanguagesMapper(MapperBase):
    id = "metadata.languages"

    def map_value(self, src_metadata, ctx, logger):
        """Mapping and converting of languages."""
        languages = src_metadata.get("languages", [])
        mapped_langs = []
        for lang in languages:
            try:
                language = pycountry.languages.get(alpha_2=lang.lower())

                if not language:
                    ctx.errors.append(
                        f"Language '{lang}' does not exist. INSPIRE#: {ctx.inspire_id}."
                    )
                    return []
                mapped_langs.append({"id": language.alpha_3})
            except LookupError as e:
                ctx.errors.append(
                    f"Failed mapping language '{lang}'. INSPIRE#: {ctx.inspire_id}. Error: {str(e)}."
                )
        return mapped_langs
