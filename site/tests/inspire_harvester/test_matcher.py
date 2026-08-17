# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""INSPIRE harvester matcher tests."""
from unittest.mock import Mock, patch

import pytest
from invenio_vocabularies.datastreams.errors import WriterError
from sqlalchemy.orm.exc import NoResultFound

from cds_rdm.inspire_harvester.load.matcher import RecordMatcher

from .utils import legacy_entry


@patch("cds_rdm.inspire_harvester.load.matcher.RecordMatcher._get_legacy_cds")
@patch("cds_rdm.inspire_harvester.load.matcher.current_rdm_records_service.search")
@patch("cds_rdm.inspire_harvester.load.matcher.get_pid_by_legacy_recid")
def test_matcher_skips_fallback_search_when_legacy_pidstore_lookup_misses(
    mock_get_pid, mock_search, mock_get_legacy, running_app
):
    """Legacy recid pidstore miss probes old CDS and skips the search-filter chain."""
    matcher = RecordMatcher()
    logger = Mock()
    stream_entry = legacy_entry("2633876")
    mock_get_pid.side_effect = NoResultFound()
    mock_get_legacy.return_value = Mock(status_code=200, headers={})

    result = matcher.match(stream_entry, inspire_id="111", logger=logger)

    assert result.unmigrated is True
    assert result.found is False
    assert result.ambiguous is False
    mock_search.assert_not_called()
    mock_get_legacy.assert_called_once_with("2633876")


@patch("cds_rdm.inspire_harvester.load.matcher.current_rdm_records_service.read_latest")
@patch("cds_rdm.inspire_harvester.load.matcher.get_pid_by_legacy_recid")
def test_matcher_finds_record_by_legacy_recid(
    mock_get_pid, mock_read_latest, running_app
):
    """Pidstore hit on the CDS recid updates that record."""
    matcher = RecordMatcher()
    logger = Mock()
    stream_entry = legacy_entry("2765541")
    mock_get_pid.return_value = Mock(pid_value="parent-1")
    mock_read_latest.return_value = Mock(id="rec-1")

    result = matcher.match(stream_entry, inspire_id="111", logger=logger)

    assert result.found is True
    assert result.record_pid == "rec-1"


@patch("cds_rdm.inspire_harvester.load.matcher.current_rdm_records_service.read_latest")
@patch("cds_rdm.inspire_harvester.load.matcher.get_pid_by_legacy_recid")
def test_matcher_tries_each_legacy_cds_id_until_pidstore_hits(
    mock_get_pid, mock_read_latest, running_app
):
    """A later CDS recid should still match when an earlier one is missing."""
    matcher = RecordMatcher()
    logger = Mock()
    stream_entry = legacy_entry("2798711", "2765541")
    mock_get_pid.side_effect = [NoResultFound(), Mock(pid_value="parent-1")]
    mock_read_latest.return_value = Mock(id="rec-1")

    result = matcher.match(stream_entry, inspire_id="111", logger=logger)

    assert result.found is True
    assert result.record_pid == "rec-1"
    assert mock_get_pid.call_count == 2


@patch("cds_rdm.inspire_harvester.load.matcher.current_rdm_records_service.search")
@patch("cds_rdm.inspire_harvester.load.matcher.current_rdm_records_service.read_latest")
@patch("cds_rdm.inspire_harvester.load.matcher.get_pid_by_legacy_recid")
def test_matcher_is_ambiguous_when_legacy_ids_hit_different_records(
    mock_get_pid, mock_read_latest, mock_search, running_app
):
    """Two CDS recids pointing at different records should not pick one to update."""
    matcher = RecordMatcher()
    logger = Mock()
    stream_entry = legacy_entry("2765541", "2798711")
    mock_get_pid.side_effect = [Mock(pid_value="parent-1"), Mock(pid_value="parent-2")]
    mock_read_latest.side_effect = [Mock(id="rec-1"), Mock(id="rec-2")]

    result = matcher.match(stream_entry, inspire_id="111", logger=logger)

    assert result.ambiguous is True
    assert result.found is False
    assert result.matched_ids == ["rec-1", "rec-2"]
    mock_search.assert_not_called()


@patch("cds_rdm.inspire_harvester.load.matcher.RecordMatcher._get_legacy_cds")
@patch("cds_rdm.inspire_harvester.load.matcher.get_pid_by_legacy_recid")
def test_matcher_skips_when_one_of_two_legacy_ids_is_still_on_cds(
    mock_get_pid, mock_get_legacy, running_app
):
    """A later CDS recid still on old CDS should skip even if an earlier one 404s."""
    matcher = RecordMatcher()
    logger = Mock()
    stream_entry = legacy_entry("2798711", "2765541")
    mock_get_pid.side_effect = NoResultFound()
    mock_get_legacy.side_effect = [
        Mock(status_code=404, headers={}),
        Mock(status_code=200, headers={}),
    ]

    result = matcher.match(stream_entry, inspire_id="111", logger=logger)

    assert result.unmigrated is True
    assert result.matched_ids == ["2765541"]
    assert mock_get_legacy.call_count == 2


@patch("cds_rdm.inspire_harvester.load.matcher.RecordMatcher._get_legacy_cds")
@patch("cds_rdm.inspire_harvester.load.matcher.get_pid_by_legacy_recid")
def test_matcher_errors_when_one_of_two_legacy_ids_redirects_to_rdm(
    mock_get_pid, mock_get_legacy, running_app
):
    """A redirected CDS recid should error even if another id is still on old CDS."""
    matcher = RecordMatcher()
    logger = Mock()
    stream_entry = legacy_entry("2765541", "2798711")
    mock_get_pid.side_effect = NoResultFound()
    mock_get_legacy.side_effect = [
        Mock(status_code=200, headers={}),
        Mock(
            status_code=302,
            headers={"Location": "https://repository.cern/records/abcde-fghij"},
        ),
    ]

    with pytest.raises(WriterError, match="lrecid is missing from pidstore"):
        matcher.match(stream_entry, inspire_id="111", logger=logger)


@patch("cds_rdm.inspire_harvester.load.matcher.RecordMatcher._get_legacy_cds")
@patch("cds_rdm.inspire_harvester.load.matcher.get_pid_by_legacy_recid")
def test_matcher_errors_when_all_legacy_ids_are_missing_on_cds(
    mock_get_pid, mock_get_legacy, running_app
):
    """All unresolved CDS recids 404ing should error, not create."""
    matcher = RecordMatcher()
    logger = Mock()
    stream_entry = legacy_entry("2798711", "2765541")
    mock_get_pid.side_effect = NoResultFound()
    mock_get_legacy.return_value = Mock(status_code=404, headers={})

    with pytest.raises(WriterError, match="was not found in the old CDS"):
        matcher.match(stream_entry, inspire_id="111", logger=logger)

    assert mock_get_legacy.call_count == 2


@patch("cds_rdm.inspire_harvester.load.matcher.RecordMatcher._get_legacy_cds")
@patch("cds_rdm.inspire_harvester.load.matcher.get_pid_by_legacy_recid")
def test_matcher_errors_on_unexpected_legacy_cds_status(
    mock_get_pid, mock_get_legacy, running_app
):
    """Unexpected old-CDS responses should fail loudly."""
    matcher = RecordMatcher()
    logger = Mock()
    stream_entry = legacy_entry("2633876")
    mock_get_pid.side_effect = NoResultFound()
    mock_get_legacy.return_value = Mock(status_code=500, headers={})

    with pytest.raises(WriterError, match="Unexpected response from old CDS"):
        matcher.match(stream_entry, inspire_id="111", logger=logger)
