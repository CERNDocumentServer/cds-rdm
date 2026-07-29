# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the GPL-2.0 License; see LICENSE file for more details.

"""ISNPIRE harvester reader tests."""

from unittest.mock import Mock, patch

import pytest
from invenio_vocabularies.datastreams.errors import ReaderError

from cds_rdm.inspire_harvester.reader import InspireHTTPReader


def test_reader_response_400(running_app):
    """Test InspireHTTPReader response error."""

    with patch("requests.get") as mock_get:
        # Create a mock response object
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Bad request"}
        mock_get.return_value = mock_response

        reader = InspireHTTPReader(inspire_id="1234")

        with pytest.raises(ReaderError) as e:
            list(reader.read())
            assert str(e.value).startswith(
                "Error occurred while getting JSON data from INSPIRE. See URL: https://inspirehep.net/api/literature?q=_oai.sets%3AForCDS+AND+id%3A1234. Error message: "
            )


def test_reader_empty_results(running_app, caplog):
    """Test InspireHTTPReader no results found."""
    no_results_json = {"hits": {"hits": [], "total": 0}, "links": {}}

    with patch("requests.get") as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = no_results_json

        mock_get.return_value = mock_response

        reader = InspireHTTPReader(inspire_id="1234")
        list(reader.read())

        # check that stuff was logged
        assert "No results found when querying INSPIRE. See URL: " in caplog.text


def test_reader_success(running_app):
    """Test InspireHTTPReader successfull response."""

    reader = InspireHTTPReader(since="2024-11-11", until="2025-01-11")

    for data in reader.read():
        assert len(data) > 0
        assert "metadata" in data
        assert "id" in data
        assert "links" in data


def test_reader_recovers_missing_records(running_app, caplog):
    """Test reader recovers records skipped by mid-harvest pagination shifts."""
    page_1 = {
        "hits": {
            "total": 6,
            "hits": [{"id": "1"}, {"id": "2"}, {"id": "3"}],
        },
        "links": {
            "next": "https://inspirehep.net/api/literature?q=test&page=2",
        },
    }
    # Record 4 moved to page 1 after a live update, so page 2 no longer has it.
    page_2 = {
        "hits": {
            "total": 6,
            "hits": [{"id": "5"}, {"id": "6"}],
        },
        "links": {},
    }
    ids_page = {
        "hits": {
            "total": 6,
            "hits": [{"id": str(i)} for i in range(1, 7)],
        },
        "links": {},
    }
    missing_record = {
        "hits": {
            "total": 1,
            "hits": [{"id": "4", "metadata": {"titles": [{"title": "Missing"}]}}],
        },
        "links": {},
    }

    def side_effect(url, headers=None):
        mock_response = Mock()
        mock_response.status_code = 200
        if "fields=id" in url:
            mock_response.json.return_value = ids_page
        elif "id%3A4" in url or "id:4" in url:
            mock_response.json.return_value = missing_record
        elif "page=2" in url:
            mock_response.json.return_value = page_2
        else:
            mock_response.json.return_value = page_1
        return mock_response

    with patch("requests.get", side_effect=side_effect):
        reader = InspireHTTPReader(since="2024-01-01", until="2024-01-02")
        records = list(reader.read())

    assert [str(r["id"]) for r in records] == ["1", "2", "3", "5", "6", "4"]
    assert "Re-fetching missing INSPIRE records." in caplog.text
    assert "missing=1" in caplog.text
    assert "4" in caplog.text


def test_reader_recovers_when_count_matches(running_app, caplog):
    """Test reader recovers when counts match but query IDs differ."""
    page_1 = {
        "hits": {
            "total": 6,
            "hits": [{"id": "1"}, {"id": "2"}, {"id": "3"}],
        },
        "links": {
            "next": "https://inspirehep.net/api/literature?q=test&page=2",
        },
    }
    page_2 = {
        "hits": {
            "total": 6,
            "hits": [{"id": "4"}, {"id": "5"}, {"id": "6"}],
        },
        "links": {},
    }
    ids_page = {
        "hits": {
            "total": 6,
            "hits": [{"id": str(i)} for i in (1, 2, 3, 5, 6, 7)],
        },
        "links": {},
    }
    missing_record = {
        "hits": {
            "total": 1,
            "hits": [{"id": "7", "metadata": {"titles": [{"title": "New"}]}}],
        },
        "links": {},
    }

    def side_effect(url, headers=None):
        mock_response = Mock()
        mock_response.status_code = 200
        if "fields=id" in url:
            mock_response.json.return_value = ids_page
        elif "id%3A7" in url or "id:7" in url:
            mock_response.json.return_value = missing_record
        elif "page=2" in url:
            mock_response.json.return_value = page_2
        else:
            mock_response.json.return_value = page_1
        return mock_response

    with patch("requests.get", side_effect=side_effect):
        reader = InspireHTTPReader(since="2024-01-01", until="2024-01-02")
        records = list(reader.read())

    assert [str(r["id"]) for r in records] == ["1", "2", "3", "4", "5", "6", "7"]
    assert "Re-fetching missing INSPIRE records." in caplog.text


def test_reader_skips_recovery_for_single_page(running_app, caplog):
    """Single-page harvests skip the ID scan (no pagination skip risk)."""
    page_1 = {
        "hits": {
            "total": 2,
            "hits": [{"id": "1"}, {"id": "2"}],
        },
        "links": {},
    }

    def side_effect(url, headers=None):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = page_1
        return mock_response

    with patch("requests.get", side_effect=side_effect) as mock_get:
        reader = InspireHTTPReader(since="2024-01-01", until="2024-01-02")
        records = list(reader.read())

    assert [str(r["id"]) for r in records] == ["1", "2"]
    assert "Re-fetching missing INSPIRE records." not in caplog.text
    assert all("fields=id" not in call.args[0] for call in mock_get.call_args_list)