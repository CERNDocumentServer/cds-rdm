# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Views tests."""

from copy import deepcopy

import pytest
from flask import current_app
from invenio_access.permissions import system_identity
from invenio_rdm_records.config import RDM_SEARCH as BASE_RDM_SEARCH
from invenio_rdm_records.proxies import current_rdm_records_service as service
from invenio_records_resources.services.records.queryparser import (
    QueryParser,
    SearchFieldTransformer,
)

from cds_rdm.views import get_linked_records_search_query

SEARCH_ALIAS_MAPPING = {
    "identifier": "metadata.identifiers.identifier",
    "cdsrn": "metadata.identifiers.identifier",
    "report_number": "metadata.identifiers.identifier",
    "inspire": "metadata.related_identifiers.identifier",
    "inis": "metadata.related_identifiers.identifier",
    "indico": "metadata.related_identifiers.identifier",
    "cds": "metadata.identifiers.identifier",
    "aleph": "metadata.identifiers.identifier",
    "doi": "pids.doi.identifier",
    "language": "metadata.languages.id",
    "languages": "metadata.languages.id",
    "title": "metadata.title",
    "publisher": "metadata.publisher",
    "description": "metadata.description",
    "publication_date": "metadata.publication_date",
    "creator": "metadata.creators.person_or_org.name",
    "creators": "metadata.creators.person_or_org.name",
}


@pytest.fixture(scope="module")
def app_config(app_config):
    """Test-local app config for search alias tests."""
    app_config["SQLALCHEMY_ENGINE_OPTIONS"] = {"connect_args": {}}
    app_config["RDM_SEARCH"] = {
        **deepcopy(BASE_RDM_SEARCH),
        "query_parser_cls": QueryParser.factory(
            mapping=SEARCH_ALIAS_MAPPING,
            tree_transformer_cls=SearchFieldTransformer,
        ),
    }
    return app_config


class MockRecord:
    """Mock record object for testing."""

    def __init__(self, record_data):
        """Initialize mock record."""
        self.data = record_data


class TestGetLinkedRecordsSearchQuery:
    """Test suite for get_linked_records_search_query function."""

    def test_with_legacy_numeric_cds_ids(self):
        """Test with legacy numeric CDS identifiers."""
        record = MockRecord(
            {
                "id": "abc12-def34",
                "metadata": {
                    "related_identifiers": [
                        {"scheme": "cds", "identifier": "12345"},
                        {"scheme": "cds", "identifier": "67890"},
                    ]
                },
            }
        )

        query = get_linked_records_search_query(record)

        # Should search both by id and in metadata.identifiers for legacy IDs
        assert 'id:"12345"' in query
        assert (
            'metadata.identifiers.scheme:cds AND metadata.identifiers.identifier:"12345"'
            in query
        )
        assert 'id:"67890"' in query
        assert (
            'metadata.identifiers.scheme:cds AND metadata.identifiers.identifier:"67890"'
            in query
        )

        # Should include reverse lookup
        assert (
            'metadata.related_identifiers.scheme:cds AND metadata.related_identifiers.identifier:"abc12-def34"'
            in query
        )

        # Should exclude current record and only show published
        assert "is_published:true" in query
        assert 'NOT id:"abc12-def34"' in query

    def test_with_new_alphanumeric_pids(self):
        """Test with new alphanumeric CDS PIDs."""
        record = MockRecord(
            {
                "id": "abc12-def34",
                "metadata": {
                    "related_identifiers": [
                        {"scheme": "cds", "identifier": "xyz98-qrs76"},
                        {"scheme": "cds", "identifier": "mnp43-jkl21"},
                    ]
                },
            }
        )

        query = get_linked_records_search_query(record)

        # New PIDs should only search by id (not in metadata.identifiers)
        assert 'id:"xyz98-qrs76"' in query
        assert 'metadata.identifiers.identifier:"xyz98-qrs76"' not in query
        assert 'id:"mnp43-jkl21"' in query
        assert 'metadata.identifiers.identifier:"mnp43-jkl21"' not in query

        # Should include reverse lookup
        assert (
            'metadata.related_identifiers.scheme:cds AND metadata.related_identifiers.identifier:"abc12-def34"'
            in query
        )

    def test_with_mixed_legacy_and_new_ids(self):
        """Test with both legacy numeric and new alphanumeric identifiers."""
        record = MockRecord(
            {
                "id": "abc12-def34",
                "metadata": {
                    "related_identifiers": [
                        {"scheme": "cds", "identifier": "12345"},  # legacy
                        {"scheme": "cds", "identifier": "xyz98-qrs76"},  # new
                    ]
                },
            }
        )

        query = get_linked_records_search_query(record)

        # Legacy should search both ways
        assert 'id:"12345"' in query
        assert (
            'metadata.identifiers.scheme:cds AND metadata.identifiers.identifier:"12345"'
            in query
        )

        # New should only search by id
        assert 'id:"xyz98-qrs76"' in query
        assert 'metadata.identifiers.identifier:"xyz98-qrs76"' not in query

    def test_with_non_cds_identifiers(self):
        """Test that non-CDS identifiers are ignored."""
        record = MockRecord(
            {
                "id": "abc12-def34",
                "metadata": {
                    "related_identifiers": [
                        {"scheme": "doi", "identifier": "10.1234/foo"},
                        {"scheme": "inspire", "identifier": "12345"},
                        {"scheme": "cds", "identifier": "67890"},
                    ]
                },
            }
        )

        query = get_linked_records_search_query(record)

        # Should only include CDS identifier
        assert "67890" in query
        assert "10.1234/foo" not in query
        assert "inspire" not in query
        assert "doi" not in query

    def test_with_no_related_identifiers(self):
        """Test with record that has no related_identifiers."""
        record = MockRecord({"id": "abc12-def34", "metadata": {}})

        query = get_linked_records_search_query(record)

        # Should still include reverse lookup
        assert (
            'metadata.related_identifiers.scheme:cds AND metadata.related_identifiers.identifier:"abc12-def34"'
            in query
        )
        assert "is_published:true" in query
        assert 'NOT id:"abc12-def34"' in query

    def test_with_empty_related_identifiers(self):
        """Test with empty related_identifiers array."""
        record = MockRecord(
            {"id": "abc12-def34", "metadata": {"related_identifiers": []}}
        )

        query = get_linked_records_search_query(record)

        # Should still include reverse lookup
        assert (
            'metadata.related_identifiers.scheme:cds AND metadata.related_identifiers.identifier:"abc12-def34"'
            in query
        )
        assert "is_published:true" in query

    def test_with_missing_identifier_field(self):
        """Test with related_identifiers that have missing identifier field."""
        record = MockRecord(
            {
                "id": "abc12-def34",
                "metadata": {
                    "related_identifiers": [
                        {"scheme": "cds"},  # missing identifier
                        {"scheme": "cds", "identifier": "12345"},
                    ]
                },
            }
        )

        query = get_linked_records_search_query(record)

        # Should only include the valid identifier
        assert "12345" in query

    def test_query_uses_or_operator(self):
        """Test that multiple identifiers are combined with OR."""
        record = MockRecord(
            {
                "id": "abc12-def34",
                "metadata": {
                    "related_identifiers": [
                        {"scheme": "cds", "identifier": "12345"},
                        {"scheme": "cds", "identifier": "67890"},
                    ]
                },
            }
        )

        query = get_linked_records_search_query(record)

        # Should use OR to combine query parts
        assert " OR " in query

    def test_query_excludes_current_record(self):
        """Test that the current record is excluded from results."""
        record = MockRecord(
            {
                "id": "abc12-def34",
                "metadata": {
                    "related_identifiers": [
                        {"scheme": "cds", "identifier": "12345"},
                    ]
                },
            }
        )

        query = get_linked_records_search_query(record)

        # Should exclude the current record
        assert 'NOT id:"abc12-def34"' in query

    def test_query_filters_published_only(self):
        """Test that query filters for published records only."""
        record = MockRecord(
            {
                "id": "abc12-def34",
                "metadata": {
                    "related_identifiers": [
                        {"scheme": "cds", "identifier": "12345"},
                    ]
                },
            }
        )

        query = get_linked_records_search_query(record)

        # Should only include published records
        assert "is_published:true" in query

    def test_reverse_lookup_always_included(self):
        """Test that reverse lookup is always included in the query."""
        # Test with related identifiers
        record_with_ids = MockRecord(
            {
                "id": "abc12-def34",
                "metadata": {
                    "related_identifiers": [
                        {"scheme": "cds", "identifier": "12345"},
                    ]
                },
            }
        )

        query = get_linked_records_search_query(record_with_ids)
        assert (
            'metadata.related_identifiers.scheme:cds AND metadata.related_identifiers.identifier:"abc12-def34"'
            in query
        )

        # Test without related identifiers
        record_no_ids = MockRecord({"id": "xyz98-qrs76", "metadata": {}})

        query = get_linked_records_search_query(record_no_ids)
        assert (
            'metadata.related_identifiers.scheme:cds AND metadata.related_identifiers.identifier:"xyz98-qrs76"'
            in query
        )

    def test_legacy_id_pattern_matching(self):
        """Test that only fully numeric IDs are treated as legacy."""
        record = MockRecord(
            {
                "id": "abc12-def34",
                "metadata": {
                    "related_identifiers": [
                        {"scheme": "cds", "identifier": "12345"},  # legacy
                        {"scheme": "cds", "identifier": "abc123"},  # not legacy
                        {"scheme": "cds", "identifier": "123abc"},  # not legacy
                        {"scheme": "cds", "identifier": "98765"},  # legacy
                    ]
                },
            }
        )

        query = get_linked_records_search_query(record)

        # Numeric IDs should search both ways
        assert 'metadata.identifiers.identifier:"12345"' in query
        assert 'metadata.identifiers.identifier:"98765"' in query

        # Alphanumeric should only search by id
        assert 'metadata.identifiers.identifier:"abc123"' not in query
        assert 'metadata.identifiers.identifier:"123abc"' not in query
        assert 'id:"abc123"' in query
        assert 'id:"123abc"' in query


    def test_with_non_cds_identifiers(self):
        """Test that non-CDS identifiers are ignored."""
        record = MockRecord({
            "id": "abc12-def34",
            "metadata": {
                "identifiers": [
                    {"scheme": "cds", "identifier": "11111"},
                    {"scheme": "cds", "identifier": "22222"},
                ]
            }
        })

        query = get_linked_records_search_query(record)

        assert 'metadata.related_identifiers.scheme:cds AND metadata.related_identifiers.identifier:"abc12-def34"' in query
        assert 'metadata.related_identifiers.scheme:cds AND metadata.related_identifiers.identifier:"11111"' in query
        assert 'metadata.related_identifiers.scheme:cds AND metadata.related_identifiers.identifier:"22222"' in query

    def _create_and_publish_record(
        self,
        service,
        identity,
        minimal_restricted_record,
        identifiers=None,
        related_identifiers=None,
        pids=None,
        metadata_updates=None,
    ):
        """Create, publish, and refresh a record for search tests."""
        new_data = deepcopy(minimal_restricted_record)

        if pids:
            new_data["pids"] = pids

        draft = service.create(identity, new_data)

        if identifiers is not None:
            draft.data["metadata"]["identifiers"] = identifiers

        if related_identifiers is not None:
            draft.data["metadata"]["related_identifiers"] = related_identifiers

        if metadata_updates:
            draft.data["metadata"].update(metadata_updates)

        if (
            identifiers is not None
            or related_identifiers is not None
            or metadata_updates is not None
        ):
            draft = service.update_draft(identity, id_=draft.id, data=draft.data)

        record = service.publish(identity, id_=draft.id)
        service.indexer.refresh()
        return record



    @pytest.mark.parametrize(
        ("alias_query", "expected_parsed_fragment", "create_kwargs"),
        [
            (
                'identifier:"IDENTIFIER-TEST-001"',
                'metadata.identifiers.identifier:"IDENTIFIER-TEST-001"',
                {
                    "identifiers": [
                        {"scheme": "cdsrn", "identifier": "IDENTIFIER-TEST-001"},
                    ]
                },
            ),
            (
                'cdsrn:"CERN-REPORT-001"',
                'metadata.identifiers.identifier:"CERN-REPORT-001"',
                {
                    "identifiers": [
                        {"scheme": "cdsrn", "identifier": "CERN-REPORT-001"},
                    ]
                },
            ),
            (
                'report_number:"CERN-REPORT-002"',
                'metadata.identifiers.identifier:"CERN-REPORT-002"',
                {
                    "identifiers": [
                        {"scheme": "cdsrn", "identifier": "CERN-REPORT-002"},
                    ]
                },
            ),
            (
                'inspire:"33333"',
                'metadata.related_identifiers.identifier:"33333"',
                {
                    "related_identifiers": [
                        {
                            "scheme": "inspire",
                            "identifier": "33333",
                            "relation_type": {"id": "isvariantformof"},
                            "resource_type": {"id": "publication-other"},
                        }
                    ]
                },
            ),
            (
                'inis:"12345"',
                'metadata.related_identifiers.identifier:"12345"',
                {
                    "related_identifiers": [
                        {
                            "scheme": "inis",
                            "identifier": "12345",
                            "relation_type": {"id": "isvariantformof"},
                            "resource_type": {"id": "publication-other"},
                        }
                    ]
                },
            ),
            (
                'indico:"12345"',
                'metadata.related_identifiers.identifier:"12345"',
                {
                    "related_identifiers": [
                        {
                            "scheme": "indico",
                            "identifier": "12345",
                            "relation_type": {"id": "isvariantformof"},
                            "resource_type": {"id": "publication-other"},
                        }
                    ]
                },
            ),
            (
                'cds:"2633033"',
                'metadata.identifiers.identifier:"2633033"',
                {
                    "identifiers": [
                        {"scheme": "cds", "identifier": "2633033"},
                    ]
                },
            ),
            (
                'aleph:"000181238CER"',
                'metadata.identifiers.identifier:"000181238CER"',
                {
                    "identifiers": [
                        {"scheme": "aleph", "identifier": "000181238CER"},
                    ]
                },
            ),
            (
                'doi:"10.1234/test-doi-001"',
                'pids.doi.identifier',
                {
                    "pids": {
                        "doi": {
                            "identifier": "10.1234/test-doi-001",
                            "provider": "external",
                        }
                    }
                },
            ),
            (
                'language:"eng"',
                'metadata.languages.id:"eng"',
                {
                    "metadata_updates": {
                        "languages": [{"id": "eng"}, {"id": "spa"}]
                    }
                },
            ),
            (
                'languages:"spa"',
                'metadata.languages.id:"spa"',
                {
                    "metadata_updates": {
                        "languages": [{"id": "eng"}, {"id": "spa"}]
                    }
                },
            ),
            (
                'title:"French Courses"',
                'metadata.title:"French Courses"',
                {
                    "metadata_updates": {
                        "title": "French Courses",
                    }
                },
            ),
            (
                'publisher:"CERN"',
                'metadata.publisher:"CERN"',
                {
                    "metadata_updates": {
                        "publisher": "CERN",
                    }
                },
            ),
            (
                'description:"FrenchCourseAliasTest"',
                'metadata.description:"FrenchCourseAliasTest"',
                {
                    "metadata_updates": {
                        "description": "FrenchCourseAliasTest",
                    }
                },
            ),
            (
                'publication_date:"2012-11-28"',
                'metadata.publication_date:"2012-11-28"',
                {
                    "metadata_updates": {
                        "publication_date": "2012-11-28",
                    }
                },
            ),
            (
                'creator:"CERN"',
                'metadata.creators.person_or_org.name:"CERN"',
                {
                    "metadata_updates": {
                        "creators": [
                            {
                                "person_or_org": {
                                    "type": "organizational",
                                    "name": "CERN",
                                }
                            }
                        ]
                    }
                },
            ),
            (
                'creators:"CERN"',
                'metadata.creators.person_or_org.name:"CERN"',
                {
                    "metadata_updates": {
                        "creators": [
                            {
                                "person_or_org": {
                                    "type": "organizational",
                                    "name": "CERN",
                                }
                            }
                        ]
                    }
                },
            ),
        ],
    )
    def test_search_alias_returns_record(
        self,
        db,
        location,
        resource_type_v,
        relation_type_v,
        languages_v,
        minimal_restricted_record,
        search,
        search_clear,
        alias_query,
        expected_parsed_fragment,
        create_kwargs,
    ):
        record = self._create_and_publish_record(
            service,
            system_identity,
            minimal_restricted_record,
            identifiers=create_kwargs.get("identifiers"),
            related_identifiers=create_kwargs.get("related_identifiers"),
            pids=create_kwargs.get("pids"),
            metadata_updates=create_kwargs.get("metadata_updates"),
        )

        parser = current_app.config["RDM_SEARCH"]["query_parser_cls"]()
        parsed = str(parser.parse(alias_query))

        assert expected_parsed_fragment in parsed

        result = service.search(
            system_identity,
            params={"q": alias_query},
        )

        assert result.total == 1
        hit_ids = [hit["id"] for hit in result.hits]
        assert record.id in hit_ids