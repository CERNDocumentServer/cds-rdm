# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Views tests."""
import pytest

from cds_rdm.views import get_linked_records_search_query


class MockRecord:
    """Mock record object for testing."""

    def __init__(self, record_data):
        """Initialize mock record."""
        self.data = record_data


class TestGetLinkedRecordsSearchQuery:
    """Test suite for get_linked_records_search_query function."""

    def test_with_legacy_numeric_cds_ids(self):
        """Test with legacy numeric CDS identifiers."""
        record = MockRecord({
            "id": "abc12-def34",
            "metadata": {
                "related_identifiers": [
                    {"scheme": "cds", "identifier": "12345"},
                    {"scheme": "cds", "identifier": "67890"},
                ]
            }
        })

        query = get_linked_records_search_query(record)

        # Should search both by id and in metadata.identifiers for legacy IDs
        assert 'id:"12345"' in query
        assert 'metadata.identifiers.scheme:cds AND metadata.identifiers.identifier:"12345"' in query
        assert 'id:"67890"' in query
        assert 'metadata.identifiers.scheme:cds AND metadata.identifiers.identifier:"67890"' in query

        # Should include reverse lookup
        assert 'metadata.related_identifiers.scheme:cds AND metadata.related_identifiers.identifier:"abc12-def34"' in query

        # Should exclude current record and only show published
        assert 'is_published:true' in query
        assert 'NOT id:"abc12-def34"' in query

    def test_with_new_alphanumeric_pids(self):
        """Test with new alphanumeric CDS PIDs."""
        record = MockRecord({
            "id": "abc12-def34",
            "metadata": {
                "related_identifiers": [
                    {"scheme": "cds", "identifier": "xyz98-qrs76"},
                    {"scheme": "cds", "identifier": "mnp43-jkl21"},
                ]
            }
        })

        query = get_linked_records_search_query(record)

        # New PIDs should only search by id (not in metadata.identifiers)
        assert 'id:"xyz98-qrs76"' in query
        assert 'metadata.identifiers.identifier:"xyz98-qrs76"' not in query
        assert 'id:"mnp43-jkl21"' in query
        assert 'metadata.identifiers.identifier:"mnp43-jkl21"' not in query

        # Should include reverse lookup
        assert 'metadata.related_identifiers.scheme:cds AND metadata.related_identifiers.identifier:"abc12-def34"' in query

    def test_with_mixed_legacy_and_new_ids(self):
        """Test with both legacy numeric and new alphanumeric identifiers."""
        record = MockRecord({
            "id": "abc12-def34",
            "metadata": {
                "related_identifiers": [
                    {"scheme": "cds", "identifier": "12345"},  # legacy
                    {"scheme": "cds", "identifier": "xyz98-qrs76"},  # new
                ]
            }
        })

        query = get_linked_records_search_query(record)

        # Legacy should search both ways
        assert 'id:"12345"' in query
        assert 'metadata.identifiers.scheme:cds AND metadata.identifiers.identifier:"12345"' in query

        # New should only search by id
        assert 'id:"xyz98-qrs76"' in query
        assert 'metadata.identifiers.identifier:"xyz98-qrs76"' not in query

    def test_with_non_cds_identifiers(self):
        """Test that non-CDS identifiers are ignored."""
        record = MockRecord({
            "id": "abc12-def34",
            "metadata": {
                "related_identifiers": [
                    {"scheme": "doi", "identifier": "10.1234/foo"},
                    {"scheme": "inspire", "identifier": "12345"},
                    {"scheme": "cds", "identifier": "67890"},
                ]
            }
        })

        query = get_linked_records_search_query(record)

        # Should only include CDS identifier
        assert '67890' in query
        assert '10.1234/foo' not in query
        assert 'inspire' not in query
        assert 'doi' not in query

    def test_with_no_related_identifiers(self):
        """Test with record that has no related_identifiers."""
        record = MockRecord({
            "id": "abc12-def34",
            "metadata": {}
        })

        query = get_linked_records_search_query(record)

        # Should still include reverse lookup
        assert 'metadata.related_identifiers.scheme:cds AND metadata.related_identifiers.identifier:"abc12-def34"' in query
        assert 'is_published:true' in query
        assert 'NOT id:"abc12-def34"' in query

    def test_with_empty_related_identifiers(self):
        """Test with empty related_identifiers array."""
        record = MockRecord({
            "id": "abc12-def34",
            "metadata": {
                "related_identifiers": []
            }
        })

        query = get_linked_records_search_query(record)

        # Should still include reverse lookup
        assert 'metadata.related_identifiers.scheme:cds AND metadata.related_identifiers.identifier:"abc12-def34"' in query
        assert 'is_published:true' in query

    def test_with_missing_identifier_field(self):
        """Test with related_identifiers that have missing identifier field."""
        record = MockRecord({
            "id": "abc12-def34",
            "metadata": {
                "related_identifiers": [
                    {"scheme": "cds"},  # missing identifier
                    {"scheme": "cds", "identifier": "12345"},
                ]
            }
        })

        query = get_linked_records_search_query(record)

        # Should only include the valid identifier
        assert '12345' in query

    def test_query_uses_or_operator(self):
        """Test that multiple identifiers are combined with OR."""
        record = MockRecord({
            "id": "abc12-def34",
            "metadata": {
                "related_identifiers": [
                    {"scheme": "cds", "identifier": "12345"},
                    {"scheme": "cds", "identifier": "67890"},
                ]
            }
        })

        query = get_linked_records_search_query(record)

        # Should use OR to combine query parts
        assert ' OR ' in query

    def test_query_excludes_current_record(self):
        """Test that the current record is excluded from results."""
        record = MockRecord({
            "id": "abc12-def34",
            "metadata": {
                "related_identifiers": [
                    {"scheme": "cds", "identifier": "12345"},
                ]
            }
        })

        query = get_linked_records_search_query(record)

        # Should exclude the current record
        assert 'NOT id:"abc12-def34"' in query

    def test_query_filters_published_only(self):
        """Test that query filters for published records only."""
        record = MockRecord({
            "id": "abc12-def34",
            "metadata": {
                "related_identifiers": [
                    {"scheme": "cds", "identifier": "12345"},
                ]
            }
        })

        query = get_linked_records_search_query(record)

        # Should only include published records
        assert 'is_published:true' in query

    def test_reverse_lookup_always_included(self):
        """Test that reverse lookup is always included in the query."""
        # Test with related identifiers
        record_with_ids = MockRecord({
            "id": "abc12-def34",
            "metadata": {
                "related_identifiers": [
                    {"scheme": "cds", "identifier": "12345"},
                ]
            }
        })

        query = get_linked_records_search_query(record_with_ids)
        assert 'metadata.related_identifiers.scheme:cds AND metadata.related_identifiers.identifier:"abc12-def34"' in query

        # Test without related identifiers
        record_no_ids = MockRecord({
            "id": "xyz98-qrs76",
            "metadata": {}
        })

        query = get_linked_records_search_query(record_no_ids)
        assert 'metadata.related_identifiers.scheme:cds AND metadata.related_identifiers.identifier:"xyz98-qrs76"' in query

    def test_legacy_id_pattern_matching(self):
        """Test that only fully numeric IDs are treated as legacy."""
        record = MockRecord({
            "id": "abc12-def34",
            "metadata": {
                "related_identifiers": [
                    {"scheme": "cds", "identifier": "12345"},      # legacy
                    {"scheme": "cds", "identifier": "abc123"},     # not legacy
                    {"scheme": "cds", "identifier": "123abc"},     # not legacy
                    {"scheme": "cds", "identifier": "98765"},      # legacy
                ]
            }
        })

        query = get_linked_records_search_query(record)

        # Numeric IDs should search both ways
        assert 'metadata.identifiers.identifier:"12345"' in query
        assert 'metadata.identifiers.identifier:"98765"' in query

        # Alphanumeric should only search by id
        assert 'metadata.identifiers.identifier:"abc123"' not in query
        assert 'metadata.identifiers.identifier:"123abc"' not in query
        assert 'id:"abc123"' in query
        assert 'id:"123abc"' in query
