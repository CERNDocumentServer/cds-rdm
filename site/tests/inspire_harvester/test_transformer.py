# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the GPL-2.0 License; see LICENSE file for more details.

"""INSPIRE harvester transformer tests."""
from unittest.mock import Mock, patch

from edtf.parser.grammar import ParseException

from cds_rdm.inspire_harvester.logger import Logger
from cds_rdm.inspire_harvester.transform.context import MetadataSerializationContext
from cds_rdm.inspire_harvester.transform.mappers.basic_metadata import (
    AdditionalDescriptionsMapper,
    AdditionalTitlesMapper,
    CopyrightMapper,
    DescriptionMapper,
    LanguagesMapper,
    PublicationDateMapper,
    PublisherMapper,
    ResourceTypeMapper,
    SubjectsMapper,
    TitleMapper,
)
from cds_rdm.inspire_harvester.transform.mappers.contributors import (
    AuthorsMapper,
    ContributorsMapper,
    CreatibutorsMapper,
)
from cds_rdm.inspire_harvester.transform.mappers.custom_fields import ImprintMapper
from cds_rdm.inspire_harvester.transform.mappers.files import FilesMapper
from cds_rdm.inspire_harvester.transform.mappers.identifiers import (
    DOIMapper,
    IdentifiersMapper,
    RelatedIdentifiersMapper,
)
from cds_rdm.inspire_harvester.transform.resource_types import ResourceType
from cds_rdm.inspire_harvester.transform.transform_entry import Inspire2RDM


@patch("cds_rdm.inspire_harvester.transform.mappers.identifiers.normalize_isbn")
def test_transform_related_identifiers(mock_normalize_isbn, running_app):
    """Test RelatedIdentifiersMapper."""
    mock_normalize_isbn.return_value = "978-0-123456-78-9"

    src_metadata = {
        "persistent_identifiers": [
            {"schema": "arXiv", "value": "1234.5678"},
            {"schema": "URN", "value": "urn:nbn:de:hebis:77-25439"},
            {"schema": "ARK", "value": "ark_value"},
        ],
        "external_system_identifiers": [{"schema": "CDS", "value": "2633876"}],
        "isbns": [{"value": "978-0-123456-78-9"}],
        "arxiv_eprints": [{"value": "1234.5678"}],
    }
    ctx = MetadataSerializationContext(
        resource_type=ResourceType.OTHER, inspire_id="12345"
    )
    logger = Logger(inspire_id="12345")
    mapper = RelatedIdentifiersMapper()

    result = mapper.map_value(src_metadata, ctx, logger)

    # Should include arXiv, INSPIRE ID, and ISBN (CDS should be in identifiers)
    assert len(result) == 6
    assert {
        "identifier": "arXiv:1234.5678",
        "scheme": "arxiv",
        "relation_type": {"id": "isvariantformof"},
        "resource_type": {"id": "publication-other"},
    } in result
    assert {
        "identifier": "12345",
        "scheme": "inspire",
        "relation_type": {"id": "isvariantformof"},
        "resource_type": {"id": "publication-other"},
    } in result
    assert {
        "identifier": "978-0-123456-78-9",
        "scheme": "isbn",
        "relation_type": {"id": "isvariantformof"},
        "resource_type": {"id": "publication-book"},
    } in result


def test_transform_identifiers(running_app):
    """Test IdentifiersMapper."""
    src_metadata = {
        "persistent_identifiers": [{"schema": "arXiv", "value": "1234.5678"}],
        "external_system_identifiers": [{"schema": "CDS", "value": "2633876"}],
        "isbns": [{"value": "978-0-123456-78-9"}],
        "arxiv_eprints": [{"value": "1234.5678"}],
    }
    ctx = MetadataSerializationContext(
        resource_type=ResourceType.OTHER, inspire_id="12345"
    )
    logger = Logger(inspire_id="12345")
    mapper = IdentifiersMapper()

    result = mapper.map_value(src_metadata, ctx, logger)

    assert len(result) == 1
    assert {"identifier": "2633876", "scheme": "cds"} in result


@patch("cds_rdm.inspire_harvester.transform.mappers.identifiers.is_doi")
def test_transform_dois_valid_external(mock_is_doi, running_app):
    """Test DOIMapper with valid external DOI."""
    mock_is_doi.return_value = True

    src_metadata = {"dois": [{"value": "10.5281/zenodo.12345"}]}
    ctx = MetadataSerializationContext(
        resource_type=ResourceType.OTHER, inspire_id="12345"
    )
    logger = Logger(inspire_id="12345")
    mapper = DOIMapper()

    result = mapper.map_value(src_metadata, ctx, logger)

    assert result["doi"]["identifier"] == "10.5281/zenodo.12345"
    assert result["doi"]["provider"] == "external"


@patch("cds_rdm.inspire_harvester.transform.mappers.identifiers.is_doi")
def test_transform_dois_valid_datacite(mock_is_doi, running_app):
    """Test DOIMapper with valid DataCite DOI."""
    mock_is_doi.return_value = True
    src_metadata = {"dois": [{"value": "10.17181/405kf-bmq61"}]}
    ctx = MetadataSerializationContext(
        resource_type=ResourceType.OTHER, inspire_id="12345"
    )
    logger = Logger(inspire_id="12345")
    mapper = DOIMapper()

    result = mapper.map_value(src_metadata, ctx, logger)

    assert result["doi"]["identifier"] == "10.17181/405kf-bmq61"
    assert result["doi"]["provider"] == "datacite"


@patch("cds_rdm.inspire_harvester.transform.mappers.identifiers.is_doi")
def test_transform_dois_valid_external_second(mock_is_doi, running_app):
    """Test DOIMapper with valid external DOI."""
    mock_is_doi.return_value = True

    src_metadata = {"dois": [{"value": "10.1000/test"}]}
    ctx = MetadataSerializationContext(
        resource_type=ResourceType.OTHER, inspire_id="12345"
    )
    logger = Logger(inspire_id="12345")
    mapper = DOIMapper()

    result = mapper.map_value(src_metadata, ctx, logger)

    assert result["doi"]["identifier"] == "10.1000/test"
    assert result["doi"]["provider"] == "external"


@patch("cds_rdm.inspire_harvester.transform.mappers.identifiers.is_doi")
def test_transform_dois_invalid(mock_is_doi, running_app):
    """Test DOIMapper with invalid DOI."""
    mock_is_doi.return_value = False

    src_metadata = {"dois": [{"value": "invalid_doi"}]}
    ctx = MetadataSerializationContext(
        resource_type=ResourceType.OTHER, inspire_id="12345"
    )
    logger = Logger(inspire_id="12345")
    mapper = DOIMapper()

    result = mapper.map_value(src_metadata, ctx, logger)

    assert result is None
    assert len(ctx.errors) == 1


def test_transform_dois_multiple(running_app):
    """Test DOIMapper with multiple DOIs."""
    src_metadata = {
        "dois": [
            {"value": "10.1000/test1"},
            {"value": "10.1000/test2"},
            {"value": "10.1000/test1"},
        ]
    }
    ctx = MetadataSerializationContext(
        resource_type=ResourceType.OTHER, inspire_id="12345"
    )
    logger = Logger(inspire_id="12345")
    mapper = DOIMapper()

    result = mapper.map_value(src_metadata, ctx, logger)
    assert result is None
    assert len(ctx.errors) == 1


def test_transform_document_type_single(running_app):
    """Test ResourceTypeDetector with single type."""
    from cds_rdm.inspire_harvester.transform.resource_types import ResourceTypeDetector

    src_metadata = {"control_number": 12345, "document_type": ["thesis"]}
    logger = Logger(inspire_id="12345")
    detector = ResourceTypeDetector(inspire_id="12345", logger=logger)

    result, errors = detector.detect(src_metadata)

    assert result == ResourceType.THESIS
    assert len(errors) == 0


def test_transform_document_type_multiple(running_app):
    """Test ResourceTypeDetector with multiple types."""
    from cds_rdm.inspire_harvester.transform.resource_types import ResourceTypeDetector

    src_metadata = {
        "control_number": 12345,
        "document_type": ["thesis", "article"],
    }
    logger = Logger(inspire_id="12345")
    detector = ResourceTypeDetector(inspire_id="12345", logger=logger)

    result, errors = detector.detect(src_metadata)

    # found thesis - should take over (highest priority)
    assert result == ResourceType.THESIS
    assert len(errors) == 0


def test_transform_document_type_unmapped(running_app):
    """Test ResourceTypeDetector with unmapped type."""
    from cds_rdm.inspire_harvester.transform.resource_types import ResourceTypeDetector

    src_metadata = {"control_number": 12345, "document_type": ["unknown_type"]}
    logger = Logger(inspire_id="12345")
    detector = ResourceTypeDetector(inspire_id="12345", logger=logger)

    result, errors = detector.detect(src_metadata)

    assert result is None
    assert len(errors) == 1
    assert "Couldn't find resource type mapping" in errors[0]


def test_transform_document_type_none(running_app):
    """Test ResourceTypeDetector with no document types."""
    from cds_rdm.inspire_harvester.transform.resource_types import ResourceTypeDetector

    src_metadata = {"control_number": 12345, "document_type": []}
    logger = Logger(inspire_id="12345")
    detector = ResourceTypeDetector(inspire_id="12345", logger=logger)

    result, errors = detector.detect(src_metadata)

    assert result is None
    assert len(errors) == 1
    assert "No document_type found" in errors[0]


def test_transform_titles_single_title(running_app):
    """Test TitleMapper and AdditionalTitlesMapper with single title."""
    src_metadata = {"titles": [{"title": "Main Title"}]}
    ctx = MetadataSerializationContext(
        resource_type=ResourceType.OTHER, inspire_id="12345"
    )
    logger = Logger(inspire_id="12345")

    title_mapper = TitleMapper()
    title = title_mapper.map_value(src_metadata, ctx, logger)

    additional_titles_mapper = AdditionalTitlesMapper()
    additional_titles = additional_titles_mapper.map_value(src_metadata, ctx, logger)

    assert title == "Main Title"
    assert additional_titles == []


def test_transform_titles_multiple_titles_with_subtitle(running_app):
    """Test TitleMapper and AdditionalTitlesMapper with multiple titles and subtitle."""
    src_metadata = {
        "titles": [
            {"title": "Main Title"},
            {"title": "Alternative Title"},
            {"title": "Title with Subtitle", "subtitle": "The Subtitle"},
        ]
    }
    ctx = MetadataSerializationContext(
        resource_type=ResourceType.OTHER, inspire_id="12345"
    )
    logger = Logger(inspire_id="12345")

    title_mapper = TitleMapper()
    title = title_mapper.map_value(src_metadata, ctx, logger)

    additional_titles_mapper = AdditionalTitlesMapper()
    additional_titles = additional_titles_mapper.map_value(src_metadata, ctx, logger)

    assert title == "Main Title"
    assert len(additional_titles) == 3
    assert {
        "title": "Alternative Title",
        "type": {"id": "alternative-title"},
    } in additional_titles
    assert {
        "title": "Title with Subtitle",
        "type": {"id": "alternative-title"},
    } in additional_titles
    assert {
        "title": "The Subtitle",
        "type": {"id": "subtitle"},
    } in additional_titles


def test_transform_creators(running_app):
    """Test AuthorsMapper."""
    src_metadata = {
        "authors": [
            {
                "first_name": "John",
                "last_name": "Doe",
                "inspire_roles": ["author"],
            },
            {
                "first_name": "Jane",
                "last_name": "Smith",
                "inspire_roles": ["supervisor"],
            },
        ],
        "corporate_author": ["CERN", "NASA"],
    }
    ctx = MetadataSerializationContext(
        resource_type=ResourceType.OTHER, inspire_id="12345"
    )
    logger = Logger(inspire_id="12345")
    mapper = AuthorsMapper()

    result = mapper.map_value(src_metadata, ctx, logger)

    # Check corporate authors
    corporate_authors = [
        c for c in result if c["person_or_org"]["type"] == "organizational"
    ]
    assert len(corporate_authors) == 2
    assert corporate_authors[0]["person_or_org"]["name"] == "CERN"
    assert corporate_authors[1]["person_or_org"]["name"] == "NASA"


def test_transform_contributors(running_app):
    """Test ContributorsMapper."""
    src_metadata = {
        "authors": [
            {
                "first_name": "John",
                "last_name": "Doe",
                "inspire_roles": ["author"],
            },
            {
                "first_name": "Jane",
                "last_name": "Smith",
                "inspire_roles": ["supervisor"],
            },
        ],
    }
    ctx = MetadataSerializationContext(
        resource_type=ResourceType.OTHER, inspire_id="12345"
    )
    logger = Logger(inspire_id="12345")
    mapper = ContributorsMapper()

    result = mapper.map_value(src_metadata, ctx, logger)

    # Should include supervisors (author went to creators)
    assert len(result) == 1  # 1 supervisor


def test_transform_creatibutors(running_app):
    """Test CreatibutorsMapper._transform_creatibutors."""
    authors = [
        {
            "first_name": "John",
            "last_name": "Doe",
            "inspire_roles": ["author"],
            "affiliations": [{"value": "CERN"}],
            "ids": [{"schema": "ORCID", "value": "0000-0000-0000-0000"}],
        }
    ]

    ctx = MetadataSerializationContext(
        resource_type=ResourceType.OTHER, inspire_id="12345"
    )
    mapper = CreatibutorsMapper()

    result = mapper._transform_creatibutors(authors, ctx)

    assert len(result) == 1
    author = result[0]
    assert author["person_or_org"]["given_name"] == "John"
    assert author["person_or_org"]["family_name"] == "Doe"
    assert author["person_or_org"]["name"] == "Doe, John"
    assert author["role"] == {"id": "author"}
    assert author["affiliations"] == [{"name": "CERN"}]
    assert author["person_or_org"]["identifiers"] == [
        {"identifier": "0000-0000-0000-0000", "scheme": "orcid"}
    ]


def test_transform_author_identifiers(running_app):
    """Test CreatibutorsMapper._transform_author_identifiers."""
    author = {
        "ids": [
            {"schema": "ORCID", "value": "0000-0000-0000-0000"},
            {"schema": "INSPIRE ID", "value": "INSPIRE-12345"},
            {"schema": "UNKNOWN", "value": "unknown"},
        ]
    }

    mapper = CreatibutorsMapper()
    result = mapper._transform_author_identifiers(author)

    assert len(result) == 2  # Only ORCID and INSPIRE ID should be included
    assert {"identifier": "0000-0000-0000-0000", "scheme": "orcid"} in result
    assert {"identifier": "INSPIRE-12345", "scheme": "inspire_author"} in result


def test_transform_author_affiliations(running_app):
    """Test CreatibutorsMapper._transform_author_affiliations."""
    author = {
        "affiliations": [
            {"value": "CERN"},
            {"value": "MIT"},
            {},  # Empty affiliation should be ignored
        ]
    }

    mapper = CreatibutorsMapper()
    result = mapper._transform_author_affiliations(author)

    assert len(result) == 2
    assert {"name": "CERN"} in result
    assert {"name": "MIT"} in result


def test_transform_copyrights_complete(running_app):
    """Test CopyrightMapper with complete copyright info."""
    src_metadata = {
        "copyright": [
            {
                "holder": "CERN",
                "year": 2023,
                "statement": "All rights reserved",
                "url": "https://cern.ch",
            }
        ]
    }
    ctx = MetadataSerializationContext(
        resource_type=ResourceType.OTHER, inspire_id="12345"
    )
    logger = Logger(inspire_id="12345")
    mapper = CopyrightMapper()

    result = mapper.map_value(src_metadata, ctx, logger)

    assert result == "© CERN 2023, All rights reserved https://cern.ch"


def test_transform_copyrights_multiple(running_app):
    """Test CopyrightMapper with multiple copyrights."""
    src_metadata = {
        "copyright": [
            {"holder": "CERN", "year": 2023},
            {"statement": "CC BY 4.0"},
        ]
    }
    ctx = MetadataSerializationContext(
        resource_type=ResourceType.OTHER, inspire_id="12345"
    )
    logger = Logger(inspire_id="12345")
    mapper = CopyrightMapper()

    result = mapper.map_value(src_metadata, ctx, logger)

    assert result == "© CERN 2023<br />© CC BY 4.0"


def test_transform_copyrights_empty(running_app):
    """Test CopyrightMapper with empty copyright."""
    src_metadata = {"copyright": [{}]}
    ctx = MetadataSerializationContext(
        resource_type=ResourceType.OTHER, inspire_id="12345"
    )
    logger = Logger(inspire_id="12345")
    mapper = CopyrightMapper()

    result = mapper.map_value(src_metadata, ctx, logger)

    assert result is None


def test_transform_abstracts(running_app):
    """Test DescriptionMapper."""
    src_metadata = {
        "abstracts": [
            {"value": "This is the main abstract"},
            {"value": "This is another abstract"},
        ]
    }
    ctx = MetadataSerializationContext(
        resource_type=ResourceType.OTHER, inspire_id="12345"
    )
    logger = Logger(inspire_id="12345")
    mapper = DescriptionMapper()

    result = mapper.map_value(src_metadata, ctx, logger)

    assert result == "This is the main abstract"


def test_transform_abstracts_empty(running_app):
    """Test DescriptionMapper with no abstracts."""
    src_metadata = {"abstracts": []}
    ctx = MetadataSerializationContext(
        resource_type=ResourceType.OTHER, inspire_id="12345"
    )
    logger = Logger(inspire_id="12345")
    mapper = DescriptionMapper()

    result = mapper.map_value(src_metadata, ctx, logger)

    assert result is None


def test_transform_subjects(running_app):
    """Test SubjectsMapper."""
    src_metadata = {
        "keywords": [
            {"value": "quantum mechanics"},
            {"value": "physics"},
            {},  # Empty keyword should be ignored
        ]
    }
    ctx = MetadataSerializationContext(
        resource_type=ResourceType.OTHER, inspire_id="12345"
    )
    logger = Logger(inspire_id="12345")
    mapper = SubjectsMapper()

    result = mapper.map_value(src_metadata, ctx, logger)

    assert len(result) == 2
    assert {"subject": "quantum mechanics"} in result
    assert {"subject": "physics"} in result


@patch("cds_rdm.inspire_harvester.transform.mappers.basic_metadata.pycountry")
def test_transform_languages(mock_pycountry, running_app):
    """Test LanguagesMapper."""
    mock_lang = Mock()
    mock_lang.alpha_3 = "eng"
    mock_pycountry.languages.get.return_value = mock_lang

    src_metadata = {"languages": ["en"]}
    ctx = MetadataSerializationContext(
        resource_type=ResourceType.OTHER, inspire_id="12345"
    )
    logger = Logger(inspire_id="12345")
    mapper = LanguagesMapper()

    result = mapper.map_value(src_metadata, ctx, logger)

    assert result == [{"id": "eng"}]


@patch("cds_rdm.inspire_harvester.transform.mappers.basic_metadata.pycountry")
def test_transform_languages_invalid(mock_pycountry, running_app):
    """Test LanguagesMapper with invalid language."""
    mock_pycountry.languages.get.return_value = None

    src_metadata = {"languages": ["invalid"]}
    ctx = MetadataSerializationContext(
        resource_type=ResourceType.OTHER, inspire_id="12345"
    )
    logger = Logger(inspire_id="12345")
    mapper = LanguagesMapper()

    result = mapper.map_value(src_metadata, ctx, logger)

    assert result == []
    assert len(ctx.errors) == 1


def test_transform_additional_descriptions(running_app):
    """Test AdditionalDescriptionsMapper."""
    src_metadata = {
        "abstracts": [
            {"value": "Main abstract"},
            {"value": "Additional abstract"},
        ],
        "book_series": [{"title": "Series Title", "volume": "Vol. 1"}],
    }
    ctx = MetadataSerializationContext(
        resource_type=ResourceType.OTHER, inspire_id="12345"
    )
    logger = Logger(inspire_id="12345")
    mapper = AdditionalDescriptionsMapper()

    result = mapper.map_value(src_metadata, ctx, logger)

    assert len(result) == 3
    assert {
        "description": "Additional abstract",
        "type": {"id": "abstract"},
    } in result
    assert {
        "description": "Series Title",
        "type": {"id": "series-information"},
    } in result
    assert {"description": "Vol. 1", "type": {"id": "series-information"}} in result


def test_transform_files(running_app):
    """Test FilesMapper."""
    src_metadata = {
        "documents": [
            {
                "filename": "test",
                "key": "abc123",
                "url": "https://example.com/file",
                "description": "Test file",
                "original_url": "https://original.com/file",
            }
        ]
    }
    ctx = MetadataSerializationContext(
        resource_type=ResourceType.OTHER, inspire_id="12345"
    )
    logger = Logger(inspire_id="12345")
    mapper = FilesMapper()

    result = mapper.map_value(src_metadata, ctx, logger)

    assert result["enabled"] is True
    assert "test.pdf" in result["entries"]

    file_entry = result["entries"]["test.pdf"]
    assert file_entry["checksum"] == "md5:abc123"
    assert file_entry["key"] == "test.pdf"
    assert file_entry["inspire_url"] == "https://example.com/file"
    assert file_entry["metadata"]["description"] == "Test file"
    assert file_entry["metadata"]["original_url"] == "https://original.com/file"


def test_transform_no_files_error(running_app):
    """Test FilesMapper with no files."""
    src_metadata = {
        "control_number": 12345,
        "documents": [],  # No documents/files
        "document_type": ["thesis"],
        "titles": [{"title": "Test Title"}],
    }
    ctx = MetadataSerializationContext(
        resource_type=ResourceType.THESIS, inspire_id="12345"
    )
    logger = Logger(inspire_id="12345")
    mapper = FilesMapper()

    result = mapper.map_value(src_metadata, ctx, logger)

    assert result == {"enabled": True, "entries": {}}


def test_transform_imprint_place(running_app):
    """Test ImprintMapper."""
    src_metadata = {
        "imprints": [{"place": "Geneva", "publisher": "CERN"}],
        "control_number": 12345,
    }
    ctx = MetadataSerializationContext(
        resource_type=ResourceType.OTHER, inspire_id="12345"
    )
    logger = Logger(inspire_id="12345")
    mapper = ImprintMapper()

    result = mapper.map_value(src_metadata, ctx, logger)

    assert "place" in result
    assert result["place"] == "Geneva"


def test_transform_imprint_place_with_isbn(running_app):
    """Test ImprintMapper with ISBN."""
    src_metadata = {
        "imprints": [{"place": "New York", "publisher": "Springer"}],
        "isbns": [{"value": "978-3-16-148410-0", "medium": "online"}],
        "control_number": 12345,
    }
    ctx = MetadataSerializationContext(
        resource_type=ResourceType.OTHER, inspire_id="12345"
    )
    logger = Logger(inspire_id="12345")
    mapper = ImprintMapper()

    result = mapper.map_value(src_metadata, ctx, logger)

    assert "place" in result
    assert result["place"] == "New York"
    assert result["isbn"] == "978-3-16-148410-0"


def test_transform_imprint_place_no_imprints(running_app):
    """Test ImprintMapper when no imprints are present."""
    src_metadata = {
        "imprints": [],
        "control_number": 12345,
    }
    ctx = MetadataSerializationContext(
        resource_type=ResourceType.OTHER, inspire_id="12345"
    )
    logger = Logger(inspire_id="12345")
    mapper = ImprintMapper()

    result = mapper.map_value(src_metadata, ctx, logger)

    assert result == {}


def test_transform_files_figures_omitted(running_app):
    """Test that figure type files are omitted from file transformation."""
    src_metadata = {
        "control_number": 12345,
        "documents": [
            {
                "filename": "thesis.pdf",
                "key": "doc123",
                "url": "https://example.com/thesis.pdf",
            }
        ],
        "figures": [
            {
                "filename": "figure1.pdf",
                "key": "fig123",
                "url": "https://example.com/figure1.pdf",
            },
            {
                "filename": "figure2.png",
                "key": "fig456",
                "url": "https://example.com/figure2.png",
            },
        ],
    }
    ctx = MetadataSerializationContext(
        resource_type=ResourceType.THESIS, inspire_id="12345"
    )
    logger = Logger(inspire_id="12345")
    mapper = FilesMapper()

    result = mapper.map_value(src_metadata, ctx, logger)

    # Documents should be included
    assert "thesis.pdf" in result["entries"]

    # Figures should be omitted/ignored (FilesMapper only processes documents)
    assert "figure1.pdf" not in result["entries"]
    assert "figure2.png" not in result["entries"]

    # Only one file (the document) should be present
    assert len(result["entries"]) == 1


def test_transform_files_pdf_extension(running_app):
    """Test FilesMapper adds .pdf extension when missing."""
    src_metadata = {
        "documents": [
            {
                "filename": "document.pdf",
                "key": "abc123",
                "url": "https://example.com/file",
            }
        ]
    }
    ctx = MetadataSerializationContext(
        resource_type=ResourceType.OTHER, inspire_id="12345"
    )
    logger = Logger(inspire_id="12345")
    mapper = FilesMapper()

    result = mapper.map_value(src_metadata, ctx, logger)

    # Should not add .pdf extension if already present
    assert "document.pdf" in result["entries"]


def test_transform_publisher(running_app):
    """Test PublisherMapper."""
    src_metadata = {"imprints": [{"publisher": "Test Publisher"}]}
    ctx = MetadataSerializationContext(
        resource_type=ResourceType.OTHER, inspire_id="12345"
    )
    logger = Logger(inspire_id="12345")
    mapper = PublisherMapper()

    publisher = mapper.map_value(src_metadata, ctx, logger)

    assert publisher == "Test Publisher"


@patch("cds_rdm.inspire_harvester.transform.mappers.basic_metadata.parse_edtf")
def test_transform_publication_date_from_imprint(mock_parse_edtf, running_app):
    """Test PublicationDateMapper from imprint."""
    mock_parse_edtf.return_value = "2023"

    src_metadata = {"imprints": [{"date": "2023"}]}
    ctx = MetadataSerializationContext(
        resource_type=ResourceType.OTHER, inspire_id="12345"
    )
    logger = Logger(inspire_id="12345")
    mapper = PublicationDateMapper()

    date = mapper.map_value(src_metadata, ctx, logger)

    assert date == "2023"


@patch("cds_rdm.inspire_harvester.transform.mappers.basic_metadata.parse_edtf")
def test_transform_publication_date_parse_exception(mock_parse_edtf, running_app):
    """Test PublicationDateMapper with parse exception."""
    mock_parse_edtf.side_effect = ParseException("Invalid date")

    src_metadata = {
        "control_number": 12345,
        "imprints": [{"date": "invalid"}],
    }
    ctx = MetadataSerializationContext(
        resource_type=ResourceType.OTHER, inspire_id="12345"
    )
    logger = Logger(inspire_id="12345")
    mapper = PublicationDateMapper()

    date = mapper.map_value(src_metadata, ctx, logger)

    assert date is None
    assert len(ctx.errors) == 1
