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
                "Error occurred while getting JSON data from INSPIRE. See URL: https://inspirehep.net/api/literature?q=%28_collections%3A%22CDS+Hidden%22+OR+_oai.sets%3AForCDS%29+AND+id%3A1234. Error message: "
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
    """Test reader harvests again when pagination skipped a record."""
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
    page_2_retry = {
        "hits": {
            "total": 6,
            "hits": [{"id": "4"}, {"id": "5"}, {"id": "6"}],
        },
        "links": {},
    }
    page_2_calls = {"n": 0}

    def side_effect(url, headers=None):
        mock_response = Mock()
        mock_response.status_code = 200
        if "page=2" in url:
            page_2_calls["n"] += 1
            mock_response.json.return_value = (
                page_2 if page_2_calls["n"] == 1 else page_2_retry
            )
        else:
            mock_response.json.return_value = page_1
        return mock_response

    with patch("requests.get", side_effect=side_effect):
        reader = InspireHTTPReader(since="2024-01-01", until="2024-01-02")
        records = list(reader.read())

    assert [str(r["id"]) for r in records] == ["1", "2", "3", "5", "6", "4"]
    assert "Harvested fewer INSPIRE records than reported; harvesting again." in caplog.text


def test_reader_does_not_retry_when_counts_match(running_app, caplog):
    """Test reader stops when harvested IDs already match hits.total."""
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
    page_1_calls = {"n": 0}

    def side_effect(url, headers=None):
        mock_response = Mock()
        mock_response.status_code = 200
        if "page=2" in url:
            mock_response.json.return_value = page_2
        else:
            page_1_calls["n"] += 1
            mock_response.json.return_value = page_1
        return mock_response

    with patch("requests.get", side_effect=side_effect) as mock_get:
        reader = InspireHTTPReader(since="2024-01-01", until="2024-01-02")
        records = list(reader.read())

    assert [str(r["id"]) for r in records] == ["1", "2", "3", "4", "5", "6"]
    assert "harvesting again" not in caplog.text
    assert page_1_calls["n"] == 1
    assert all("fields=id" not in call.args[0] for call in mock_get.call_args_list)


def test_reader_skips_recovery_for_single_page(running_app, caplog):
    """Single-page harvests do not run again when counts already match."""
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
    assert "harvesting again" not in caplog.text
    assert all("fields=id" not in call.args[0] for call in mock_get.call_args_list)
    assert mock_get.call_count == 1


def test_reader_caps_retry_passes(running_app, caplog):
    """Test reader stops after MAX_HARVEST_PASSES even if counts never match."""
    from cds_rdm.inspire_harvester.reader import MAX_HARVEST_PASSES

    # Each pass reports total=3 but only yields one new id, so the outer loop
    # would otherwise keep retrying forever as new_in_pass stays > 0.
    pass_calls = {"n": 0}

    def side_effect(url, headers=None):
        pass_calls["n"] += 1
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hits": {
                "total": 10,
                "hits": [{"id": str(pass_calls["n"])}],
            },
            "links": {},
        }
        return mock_response

    with patch("requests.get", side_effect=side_effect) as mock_get:
        reader = InspireHTTPReader(since="2024-01-01", until="2024-01-02")
        records = list(reader.read())

    assert [str(r["id"]) for r in records] == [str(i) for i in range(1, MAX_HARVEST_PASSES + 1)]
    assert mock_get.call_count == MAX_HARVEST_PASSES
    assert "after max retries; stopping" in caplog.text
