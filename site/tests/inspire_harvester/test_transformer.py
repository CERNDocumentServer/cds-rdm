# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the GPL-2.0 License; see LICENSE file for more details.

"""INSPIRE harvester transformer tests."""
from unittest.mock import Mock, patch

from edtf.parser.grammar import ParseException

from cds_rdm.inspire_harvester.transform_entry import Inspire2RDM


@patch("cds_rdm.inspire_harvester.transform_entry.normalize_isbn")
def test_transform_related_identifiers(mock_normalize_isbn, running_app):
    """Test _transform_alternate_identifiers."""
    mock_normalize_isbn.return_value = "978-0-123456-78-9"

    inspire_record = {
        "id": "12345",
        "metadata": {
            "persistent_identifiers": [
                {"schema": "arXiv", "value": "1234.5678"},
                {"schema": "URN", "value": "urn:nbn:de:hebis:77-25439"},
                {"schema": "ARK", "value": "ark_value"},
            ],
            "external_system_identifiers": [{"schema": "CDS", "value": "2633876"}],
            "isbns": [{"value": "978-0-123456-78-9"}],
            "arxiv_eprints": [{"value": "1234.5678"}],
        },
    }
    transformer = Inspire2RDM(inspire_record)

    result = transformer._transform_related_identifiers()

    # Should include arXiv, INSPIRE ID, and ISBN (CDS should be in indentifiers)
    assert len(result) == 6
    assert {
        "identifier": "1234.5678",
        "scheme": "arxiv",
        "relation_type": {"id": "isversionof"},
        "resource_type": {"id": "publication-other"},
    } in result
    assert {
        "identifier": "12345",
        "scheme": "inspire",
        "relation_type": {"id": "isversionof"},
        "resource_type": {"id": "publication-other"},
    } in result
    assert {
        "identifier": "978-0-123456-78-9",
        "scheme": "isbn",
        "relation_type": {"id": "isversionof"},
        "resource_type": {"id": "publication-book"},
    } in result


@patch("cds_rdm.inspire_harvester.transform_entry.normalize_isbn")
def test_transform_identifiers(mock_normalize_isbn, running_app):
    """Test _transform_alternate_identifiers."""
    mock_normalize_isbn.return_value = "978-0-123456-78-9"

    inspire_record = {
        "id": "12345",
        "metadata": {
            "persistent_identifiers": [{"schema": "arXiv", "value": "1234.5678"}],
            "external_system_identifiers": [{"schema": "CDS", "value": "2633876"}],
            "isbns": [{"value": "978-0-123456-78-9"}],
            "arxiv_eprints": [{"value": "1234.5678"}],
        },
    }
    transformer = Inspire2RDM(inspire_record)

    result = transformer._transform_identifiers()

    assert len(result) == 1
    assert {"identifier": "2633876", "scheme": "cds"} in result


@patch("cds_rdm.inspire_harvester.transform_entry.is_doi")
def test_transform_dois_valid_external(mock_is_doi, running_app):
    """Test _transform_dois with valid DataCite DOI."""
    mock_is_doi.return_value = True

    inspire_record = {
        "id": "12345",
        "metadata": {"dois": [{"value": "10.5281/zenodo.12345"}]},
    }
    transformer = Inspire2RDM(inspire_record)

    result = transformer._transform_dois()

    assert result["identifier"] == "10.5281/zenodo.12345"
    assert result["provider"] == "external"


@patch("cds_rdm.inspire_harvester.transform_entry.is_doi")
def test_transform_dois_valid_datacite(mock_is_doi, running_app):
    """Test _transform_dois with valid DataCite DOI."""
    mock_is_doi.return_value = True
    inspire_record = {
        "id": "12345",
        "metadata": {"dois": [{"value": "10.17181/405kf-bmq61"}]},
    }
    transformer = Inspire2RDM(inspire_record)

    result = transformer._transform_dois()

    assert result["identifier"] == "10.17181/405kf-bmq61"
    assert result["provider"] == "datacite"


@patch("cds_rdm.inspire_harvester.transform_entry.is_doi")
def test_transform_dois_valid_external(mock_is_doi, running_app):
    """Test _transform_dois with valid external DOI."""
    mock_is_doi.return_value = True

    inspire_record = {
        "id": "12345",
        "metadata": {"dois": [{"value": "10.1000/test"}]},
    }
    transformer = Inspire2RDM(inspire_record)

    result = transformer._transform_dois()

    assert result["identifier"] == "10.1000/test"
    assert result["provider"] == "external"


@patch("cds_rdm.inspire_harvester.transform_entry.is_doi")
def test_transform_dois_invalid(mock_is_doi, running_app):
    """Test _transform_dois with invalid DOI."""
    mock_is_doi.return_value = False

    inspire_record = {
        "id": "12345",
        "metadata": {"dois": [{"value": "invalid_doi"}]},
    }
    transformer = Inspire2RDM(inspire_record)

    result = transformer._transform_dois()

    assert result is None
    assert len(transformer.metadata_errors) == 1


def test_transform_dois_multiple():
    """Test _transform_dois with multiple DOIs."""
    inspire_record = {
        "id": "12345",
        "metadata": {
            "dois": [
                {"value": "10.1000/test1"},
                {"value": "10.1000/test2"},
                {"value": "10.1000/test1"},
            ]
        },
    }
    transformer = Inspire2RDM(inspire_record)

    result = transformer._transform_dois()
    assert result is None
    assert len(transformer.metadata_errors) == 1
    # assert result == [{"value": "10.1000/test1"}, {"value": "10.1000/test2"}]


def test_transform_document_type_single(running_app):
    """Test _transform_document_type with single type."""
    inspire_record = {
        "id": "12345",
        "metadata": {"control_number": 12345, "document_type": ["thesis"]},
    }
    transformer = Inspire2RDM(inspire_record)

    result = transformer._transform_document_type()

    assert result == {"id": "publication-dissertation"}


def test_transform_document_type_multiple(running_app):
    """Test _transform_document_type with multiple types."""
    inspire_record = {
        "id": "12345",
        "metadata": {
            "control_number": 12345,
            "document_type": ["thesis", "article"],
        },
    }
    transformer = Inspire2RDM(inspire_record)

    result = transformer._transform_document_type()

    assert result is None
    assert len(transformer.metadata_errors) == 1
    assert "Multiple document types found" in transformer.metadata_errors[0]


def test_transform_document_type_unmapped(running_app):
    """Test _transform_document_type with unmapped type."""
    inspire_record = {
        "id": "12345",
        "metadata": {"control_number": 12345, "document_type": ["unknown_type"]},
    }
    transformer = Inspire2RDM(inspire_record)

    result = transformer._transform_document_type()

    assert result is None
    assert len(transformer.metadata_errors) == 1
    assert "Couldn't find resource type mapping" in transformer.metadata_errors[0]


def test_transform_document_type_none(running_app):
    """Test _transform_document_type with no document types."""
    inspire_record = {
        "id": "12345",
        "metadata": {"control_number": 12345, "document_type": []},
    }
    transformer = Inspire2RDM(inspire_record)

    result = transformer._transform_document_type()

    assert result is None
    assert len(transformer.metadata_errors) == 1
    assert "No document_type found" in transformer.metadata_errors[0]


def test_transform_titles_single_title():
    """Test _transform_titles with single title."""
    inspire_record = {
        "id": "12345",
        "metadata": {"titles": [{"title": "Main Title"}]},
    }
    transformer = Inspire2RDM(inspire_record)

    title, additional_titles = transformer._transform_titles()

    assert title == "Main Title"
    assert additional_titles == []


def test_transform_titles_multiple_titles_with_subtitle():
    """Test _transform_titles with multiple titles and subtitle."""
    inspire_record = {
        "id": "12345",
        "metadata": {
            "titles": [
                {"title": "Main Title"},
                {"title": "Alternative Title"},
                {"title": "Title with Subtitle", "subtitle": "The Subtitle"},
            ]
        },
    }
    transformer = Inspire2RDM(inspire_record)

    title, additional_titles = transformer._transform_titles()

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


def test_transform_titles_exception():
    """Test _transform_titles with exception handling."""
    inspire_record = {
        "id": "12345",
        "metadata": {"titles": [None]},  # This will cause an exception
    }
    transformer = Inspire2RDM(inspire_record)

    title, additional_titles = transformer._transform_titles()

    assert title is None
    assert additional_titles is None
    assert len(transformer.metadata_errors) == 1


def test_transform_creators():
    """Test _transform_creators."""
    inspire_record = {
        "id": "12345",
        "metadata": {
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
            ]
        },
    }
    transformer = Inspire2RDM(inspire_record)

    with patch.object(transformer, "_transform_creatibutors") as mock_transform:
        mock_transform.return_value = [{"person_or_org": {"name": "Doe, John"}}]

        result = transformer._transform_creators()

        # Should only include authors, not supervisors
        mock_transform.assert_called_once()
        called_authors = mock_transform.call_args[0][0]
        assert len(called_authors) == 1
        assert called_authors[0]["inspire_roles"] == ["author"]


def test_transform_contributors():
    """Test _transform_contributors."""
    inspire_record = {
        "id": "12345",
        "metadata": {
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
        },
    }
    transformer = Inspire2RDM(inspire_record)

    with patch.object(transformer, "_transform_creatibutors") as mock_transform:
        mock_transform.return_value = [
            {
                "person_or_org": {
                    "type": "personal",
                    "name": "Smith, Jane",
                    "role": {"id": "other"},
                }
            },
        ]

        result = transformer._transform_contributors()

        # Should include supervisors and corporate authors
        assert len(result) == 3  # 1 supervisor + 2 corporate authors

        # Check corporate authors
        corporate_contributors = [
            c for c in result if c["person_or_org"]["type"] == "organizational"
        ]
        assert len(corporate_contributors) == 2
        assert corporate_contributors[0]["person_or_org"]["name"] == "CERN"
        assert corporate_contributors[1]["person_or_org"]["name"] == "NASA"


def test_transform_creatibutors():
    """Test _transform_creatibutors."""
    authors = [
        {
            "first_name": "John",
            "last_name": "Doe",
            "inspire_roles": ["author"],
            "affiliations": [{"value": "CERN"}],
            "ids": [{"schema": "ORCID", "value": "0000-0000-0000-0000"}],
        }
    ]

    inspire_record = {"id": "12345", "metadata": {}}
    transformer = Inspire2RDM(inspire_record)

    with (
        patch.object(transformer, "_transform_author_affiliations") as mock_aff,
        patch.object(transformer, "_transform_author_identifiers") as mock_ids,
    ):
        mock_aff.return_value = [{"name": "CERN"}]
        mock_ids.return_value = [
            {"identifier": "0000-0000-0000-0000", "scheme": "orcid"}
        ]

        result = transformer._transform_creatibutors(authors)

        assert len(result) == 1
        author = result[0]
        assert author["person_or_org"]["given_name"] == "John"
        assert author["person_or_org"]["family_name"] == "Doe"
        assert author["person_or_org"]["name"] == "Doe, John"
        assert author["role"] == "author"
        assert author["affiliations"] == [{"name": "CERN"}]
        assert author["person_or_org"]["identifiers"] == [
            {"identifier": "0000-0000-0000-0000", "scheme": "orcid"}
        ]


def test_transform_author_identifiers():
    """Test _transform_author_identifiers."""
    author = {
        "ids": [
            {"schema": "ORCID", "value": "0000-0000-0000-0000"},
            {"schema": "INSPIRE ID", "value": "INSPIRE-12345"},
            {"schema": "UNKNOWN", "value": "unknown"},
        ]
    }

    inspire_record = {"id": "12345", "metadata": {}}
    transformer = Inspire2RDM(inspire_record)

    result = transformer._transform_author_identifiers(author)

    assert len(result) == 2  # Only ORCID and INSPIRE ID should be included
    assert {"identifier": "0000-0000-0000-0000", "scheme": "orcid"} in result
    assert {"identifier": "INSPIRE-12345", "scheme": "inspire_author"} in result


def test_transform_author_affiliations():
    """Test _transform_author_affiliations."""
    author = {
        "affiliations": [
            {"value": "CERN"},
            {"value": "MIT"},
            {},  # Empty affiliation should be ignored
        ]
    }

    inspire_record = {"id": "12345", "metadata": {}}
    transformer = Inspire2RDM(inspire_record)

    result = transformer._transform_author_affiliations(author)

    assert len(result) == 2
    assert {"name": "CERN"} in result
    assert {"name": "MIT"} in result


def test_transform_copyrights_complete():
    """Test _transform_copyrights with complete copyright info."""
    inspire_record = {
        "id": "12345",
        "metadata": {
            "copyright": [
                {
                    "holder": "CERN",
                    "year": 2023,
                    "statement": "All rights reserved",
                    "url": "https://cern.ch",
                }
            ]
        },
    }
    transformer = Inspire2RDM(inspire_record)

    result = transformer._transform_copyrights()

    assert result == "© CERN 2023, All rights reserved https://cern.ch"


def test_transform_copyrights_multiple():
    """Test _transform_copyrights with multiple copyrights."""
    inspire_record = {
        "id": "12345",
        "metadata": {
            "copyright": [
                {"holder": "CERN", "year": 2023},
                {"statement": "CC BY 4.0"},
            ]
        },
    }
    transformer = Inspire2RDM(inspire_record)

    result = transformer._transform_copyrights()

    assert result == "© CERN 2023<br />© CC BY 4.0"


def test_transform_copyrights_empty():
    """Test _transform_copyrights with empty copyright."""
    inspire_record = {"id": "12345", "metadata": {"copyright": [{}]}}
    transformer = Inspire2RDM(inspire_record)

    result = transformer._transform_copyrights()

    assert result is None


def test_transform_abstracts():
    """Test _transform_abstracts."""
    inspire_record = {
        "id": "12345",
        "metadata": {
            "abstracts": [
                {"value": "This is the main abstract"},
                {"value": "This is another abstract"},
            ]
        },
    }
    transformer = Inspire2RDM(inspire_record)

    result = transformer._transform_abstracts()

    assert result == "This is the main abstract"


def test_transform_abstracts_empty():
    """Test _transform_abstracts with no abstracts."""
    inspire_record = {"id": "12345", "metadata": {"abstracts": []}}
    transformer = Inspire2RDM(inspire_record)

    result = transformer._transform_abstracts()

    assert result is None


def test_transform_subjects():
    """Test _transform_subjects."""
    inspire_record = {
        "id": "12345",
        "metadata": {
            "keywords": [
                {"value": "quantum mechanics"},
                {"value": "physics"},
                {},  # Empty keyword should be ignored
            ]
        },
    }
    transformer = Inspire2RDM(inspire_record)

    result = transformer._transform_subjects()

    assert len(result) == 2
    assert {"subject": "quantum mechanics"} in result
    assert {"subject": "physics"} in result


@patch("cds_rdm.inspire_harvester.transform_entry.pycountry")
def test_transform_languages(mock_pycountry):
    """Test _transform_languages."""
    mock_lang = Mock()
    mock_lang.alpha_3 = "eng"
    mock_pycountry.languages.get.return_value = mock_lang

    inspire_record = {"id": "12345", "metadata": {"languages": ["en"]}}
    transformer = Inspire2RDM(inspire_record)

    result = transformer._transform_languages()

    assert result == [{"id": "eng"}]


@patch("cds_rdm.inspire_harvester.transform_entry.pycountry")
def test_transform_languages_invalid(mock_pycountry):
    """Test _transform_languages with invalid language."""
    mock_pycountry.languages.get.return_value = None

    inspire_record = {"id": "12345", "metadata": {"languages": ["invalid"]}}
    transformer = Inspire2RDM(inspire_record)

    result = transformer._transform_languages()

    assert result is None
    assert len(transformer.metadata_errors) == 1


def test_transform_additional_descriptions():
    """Test _transform_additional_descriptions."""
    inspire_record = {
        "id": "12345",
        "metadata": {
            "abstracts": [
                {"value": "Main abstract"},
                {"value": "Additional abstract"},
            ],
            "book_series": [{"title": "Series Title", "volume": "Vol. 1"}],
        },
    }
    transformer = Inspire2RDM(inspire_record)

    result = transformer._transform_additional_descriptions()

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


def test_parse_cern_accelerator_experiment():
    """Test _parse_cern_accelerator_experiment."""
    inspire_record = {"id": "12345", "metadata": {}}
    transformer = Inspire2RDM(inspire_record)

    accelerator, experiment = transformer._parse_cern_accelerator_experiment(
        "CERN-LHC-ATLAS"
    )
    assert accelerator == "LHC"
    assert experiment == "ATLAS"

    accelerator, experiment = transformer._parse_cern_accelerator_experiment("CERN-LEP")
    assert accelerator == "LEP"
    assert experiment is None

    accelerator, experiment = transformer._parse_cern_accelerator_experiment("NOT-CERN")
    assert accelerator is None
    assert experiment is None


def test_transform_files():
    """Test transform_files method."""
    inspire_record = {
        "id": "12345",
        "metadata": {
            "documents": [
                {
                    "filename": "test",
                    "key": "abc123",
                    "url": "https://example.com/file",
                    "description": "Test file",
                    "original_url": "https://original.com/file",
                }
            ]
        },
    }
    transformer = Inspire2RDM(inspire_record)

    result, errors = transformer.transform_files()

    assert result["enabled"] is True
    assert "test.pdf" in result["entries"]

    file_entry = result["entries"]["test.pdf"]
    assert file_entry["checksum"] == "md5:abc123"
    assert file_entry["key"] == "test.pdf"
    assert file_entry["inspire_url"] == "https://example.com/file"
    assert file_entry["metadata"]["description"] == "Test file"
    assert file_entry["metadata"]["original_url"] == "https://original.com/file"


def test_transform_no_files_error():
    """Test that error is present when no files are on the record."""
    inspire_record = {
        "id": "12345",
        "metadata": {
            "control_number": 12345,
            "documents": [],  # No documents/files
            "document_type": ["thesis"],
            "titles": [{"title": "Test Title"}],
        },
    }
    transformer = Inspire2RDM(inspire_record)

    result, errors = transformer.transform_files()

    assert result == {"enabled": True, "entries": {}}


def test_transform_imprint_place():
    """Test how inspire_record["metadata"]["imprints"][0]["place"] is transformed by Inspire2RDM class."""
    inspire_record = {
        "id": "12345",
        "metadata": {
            "imprints": [{"place": "Geneva", "publisher": "CERN"}],
            "control_number": 12345,
        },
    }
    transformer = Inspire2RDM(inspire_record)

    result = transformer._transform_custom_fields()

    assert "imprint:imprint" in result
    assert result["imprint:imprint"]["place"] == "Geneva"


def test_transform_imprint_place_with_isbn():
    """Test imprint place transformation with ISBN."""
    inspire_record = {
        "id": "12345",
        "metadata": {
            "imprints": [{"place": "New York", "publisher": "Springer"}],
            "isbns": [{"value": "978-3-16-148410-0", "medium": "online"}],
            "control_number": 12345,
        },
    }
    transformer = Inspire2RDM(inspire_record)

    result = transformer._transform_custom_fields()

    assert "imprint:imprint" in result
    assert result["imprint:imprint"]["place"] == "New York"
    assert result["imprint:imprint"]["isbn"] == "978-3-16-148410-0"


def test_transform_imprint_place_no_imprints():
    """Test imprint place transformation when no imprints are present."""
    inspire_record = {
        "id": "12345",
        "metadata": {
            "imprints": [],
            "control_number": 12345,
        },
    }
    transformer = Inspire2RDM(inspire_record)

    result = transformer._transform_custom_fields()

    assert "imprint:imprint" not in result


def test_transform_imprint_place_multiple_imprints():
    """Test imprint place transformation with multiple imprints (should generate error)."""
    inspire_record = {
        "id": "12345",
        "metadata": {
            "imprints": [
                {"place": "Geneva", "publisher": "CERN"},
                {"place": "New York", "publisher": "Springer"},
            ],
            "control_number": 12345,
        },
    }
    transformer = Inspire2RDM(inspire_record)

    result = transformer._transform_custom_fields()

    assert "imprint:imprint" not in result
    assert len(transformer.metadata_errors) == 1
    assert "More than 1 imprint found" in transformer.metadata_errors[0]


def test_transform_files_figures_omitted():
    """Test that figure type files are omitted from file transformation."""
    inspire_record = {
        "id": "12345",
        "metadata": {
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
        },
    }
    transformer = Inspire2RDM(inspire_record)

    result, errors = transformer.transform_files()

    # Documents should be included
    assert "thesis.pdf" in result["entries"]

    # Figures should be omitted/ignored
    assert "figure1.pdf" not in result["entries"]
    assert "figure2.png" not in result["entries"]

    # Only one file (the document) should be present
    assert len(result["entries"]) == 1


def test_transform_files_pdf_extension():
    """Test transform_files adds .pdf extension when missing."""
    inspire_record = {
        "id": "12345",
        "metadata": {
            "documents": [
                {
                    "filename": "document.pdf",
                    "key": "abc123",
                    "url": "https://example.com/file",
                }
            ]
        },
    }
    transformer = Inspire2RDM(inspire_record)

    result, errors = transformer.transform_files()

    # Should not add .pdf extension if already present
    assert "document.pdf" in result["entries"]


def test_validate_imprint_single():
    """Test _validate_imprint with single imprint."""
    inspire_record = {
        "id": "12345",
        "metadata": {"imprints": [{"publisher": "Test Publisher"}]},
    }
    transformer = Inspire2RDM(inspire_record)

    imprint = transformer._validate_imprint()

    assert imprint == {"publisher": "Test Publisher"}


def test_validate_imprint_multiple():
    """Test _validate_imprint with multiple imprints."""
    inspire_record = {
        "id": "12345",
        "metadata": {
            "imprints": [{"publisher": "Publisher 1"}, {"publisher": "Publisher 2"}]
        },
    }
    transformer = Inspire2RDM(inspire_record)

    imprint = transformer._validate_imprint()

    assert imprint is None
    assert len(transformer.metadata_errors) == 1
    assert "More than 1 imprint found" in transformer.metadata_errors[0]


def test_validate_imprint_none():
    """Test _validate_imprint with no imprints."""
    inspire_record = {"id": "12345", "metadata": {"imprints": []}}
    transformer = Inspire2RDM(inspire_record)

    imprint = transformer._validate_imprint()

    assert imprint is None


def test_transform_publisher():
    """Test _transform_publisher."""
    inspire_record = {
        "id": "12345",
        "metadata": {"imprints": [{"publisher": "Test Publisher"}]},
    }
    transformer = Inspire2RDM(inspire_record)

    publisher = transformer._transform_publisher()

    assert publisher == "Test Publisher"


@patch("cds_rdm.inspire_harvester.transform_entry.parse_edtf")
def test_transform_publication_date_from_thesis(mock_parse_edtf):
    """Test _transform_publication_date from thesis_info."""
    mock_parse_edtf.return_value = "2023"

    inspire_record = {"id": "12345", "metadata": {"thesis_info": {"date": "2023"}}}
    transformer = Inspire2RDM(inspire_record)

    date = transformer._transform_publication_date()

    assert date == "2023"
    mock_parse_edtf.assert_called_once_with("2023")


@patch("cds_rdm.inspire_harvester.transform_entry.parse_edtf")
def test_transform_publication_date_from_imprint(mock_parse_edtf):
    """Test _transform_publication_date from imprint."""
    mock_parse_edtf.return_value = "2023"

    inspire_record = {"id": "12345", "metadata": {"imprints": [{"date": "2023"}]}}
    transformer = Inspire2RDM(inspire_record)

    date = transformer._transform_publication_date()

    assert date == "2023"


@patch("cds_rdm.inspire_harvester.transform_entry.parse_edtf")
def test_transform_publication_date_parse_exception(mock_parse_edtf):
    """Test _transform_publication_date with parse exception."""
    mock_parse_edtf.side_effect = ParseException("Invalid date")

    inspire_record = {
        "id": "12345",
        "metadata": {"control_number": 12345, "thesis_info": {"date": "invalid"}},
    }
    transformer = Inspire2RDM(inspire_record)

    date = transformer._transform_publication_date()

    assert date is None
    assert len(transformer.metadata_errors) == 1


def test_transform_publication_date_no_date():
    """Test _transform_publication_date with no date available."""
    inspire_record = {"id": "12345", "metadata": {}}
    transformer = Inspire2RDM(inspire_record)

    date = transformer._transform_publication_date()

    assert date is None
    assert len(transformer.metadata_errors) == 1
