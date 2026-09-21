# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""INSPIRE harvester matcher tests."""
from copy import deepcopy
from unittest.mock import Mock, patch

import pytest
from invenio_access.permissions import system_identity
from invenio_db import db
from invenio_rdm_records.proxies import current_rdm_records_service
from invenio_rdm_records.records.api import RDMRecord
from invenio_vocabularies.datastreams import StreamEntry
from invenio_vocabularies.datastreams.errors import WriterError
from sqlalchemy.orm.exc import NoResultFound

from cds_rdm.inspire_harvester.load.matcher import RecordMatcher

from .utils import legacy_entry


@patch("cds_rdm.inspire_harvester.load.matcher.current_rdm_records_service.search")
def test_matcher_finds_record_when_inspire_sends_parent_doi(mock_search, running_app):
    """Parent DOI alone matches (e.g. INSPIRE 3085597 / CDS 32j8w-0ep65)."""
    parent_doi = "10.17181/c4dmz-3za35"
    entry = StreamEntry(
        {
            "id": "3085597",
            "metadata": {
                "title": "Test",
                "resource_type": {"id": "publication-article"},
                "identifiers": [],
                "related_identifiers": [],
            },
            "files": {"enabled": False},
            "parent": {"access": {"owned_by": {"user": 2}}},
            "access": {"record": "public", "files": "public"},
            "pids": {"doi": {"identifier": parent_doi, "provider": "external"}},
            "_inspire_ctx": {"cds_id": None, "versions": []},
        }
    )
    mock_search.return_value = Mock(
        total=1,
        to_dict=Mock(return_value={"hits": {"hits": [{"id": "32j8w-0ep65"}]}}),
    )

    result = RecordMatcher().match(entry, inspire_id="3085597", logger=Mock())

    assert result.found is True
    assert result.record_pid == "32j8w-0ep65"
    extra_filter = mock_search.call_args.kwargs["extra_filter"]
    should = extra_filter.to_dict()["bool"]["filter"][0]["bool"]["should"]
    fields = {list(clause["terms"].keys())[0] for clause in should}
    assert fields == {
        "pids.doi.identifier.keyword",
        "parent.pids.doi.identifier.keyword",
    }


def test_parent_doi_match_returns_latest_of_many_versions(
    running_app, location, minimal_record, db
):
    """Parent DOI match returns the latest version when a lineage has many versions.

    Parent DOI uses provider ``external``, which is not registered on
    ``RDM_PARENT_PERSISTENT_IDENTIFIER_PROVIDERS``. Stamping must happen only
    after all ``publish`` calls, otherwise ``parent_pid_manager.create_all``
    raises ``ProviderNotSupportedError``.
    """
    service = current_rdm_records_service
    parent_doi = "10.9999/parent-doi-match"
    v1_doi = "10.1234/parent-doi-match-v1"
    v2_doi = "10.1234/parent-doi-match-v2"

    v1_data = deepcopy(minimal_record)
    v1_data["metadata"]["title"] = "Older version title"
    v1_data["metadata"]["publication_date"] = "2020-01-01"
    v1_data["metadata"]["resource_type"] = {"id": "publication-article"}
    draft = service.create(system_identity, v1_data)
    v1 = service.publish(system_identity, draft.id)

    draft_v2 = service.new_version(system_identity, v1.id)
    v2_data = deepcopy(draft_v2.data)
    v2_data["metadata"]["title"] = "Latest version title"
    v2_data["metadata"]["publication_date"] = "2021-01-01"
    draft_v2 = service.update_draft(system_identity, draft_v2.id, v2_data)
    v2 = service.publish(system_identity, draft_v2.id)

    # Re-read so both records share a fresh parent before stamping.
    v1 = service.read(system_identity, v1.id)
    v2 = service.read(system_identity, v2.id)
    parent = v2._record.parent
    parent.pids["doi"] = {"identifier": parent_doi, "provider": "external"}
    parent.commit()
    v1._record.pids["doi"] = {"identifier": v1_doi, "provider": "external"}
    v1._record.commit()
    v2._record.pids["doi"] = {"identifier": v2_doi, "provider": "external"}
    v2._record.commit()
    db.session.commit()
    service.indexer.index(v1._record, arguments={"refresh": True})
    service.indexer.index(v2._record, arguments={"refresh": True})
    RDMRecord.index.refresh()

    entry = StreamEntry(
        {
            "id": "3085597",
            "metadata": {
                "title": "Test",
                "resource_type": {"id": "publication-article"},
                "identifiers": [],
                "related_identifiers": [],
            },
            "files": {"enabled": False},
            "parent": {"access": {"owned_by": {"user": 2}}},
            "access": {"record": "public", "files": "public"},
            "pids": {"doi": {"identifier": parent_doi, "provider": "external"}},
            "_inspire_ctx": {"cds_id": None, "versions": []},
        }
    )
    result = RecordMatcher().match(entry, inspire_id="3085597", logger=Mock())

    assert result.found is True
    assert result.ambiguous is False
    assert result.record_pid == v2.id
    assert result.record_pid != v1.id


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
