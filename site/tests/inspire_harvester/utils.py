# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS RDM is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Pytest utils module."""
from pathlib import Path
from unittest.mock import Mock, patch

from celery import current_app
from invenio_pidstore.models import PersistentIdentifier
from invenio_vocabularies.datastreams import StreamEntry
from invenio_vocabularies.services.tasks import process_datastream

DATA_DIR = Path(__file__).parent / "data"


def mock_requests_get(
    url, mock_content, headers={"Accept": "application/json"}, stream=True
):
    """Mock inspire GET requests."""
    mock_response = Mock()
    mock_response.status_code = 200
    if "file:" in url:
        file = url.replace("file:", "")
        with open(
            DATA_DIR / file,
            "rb",
        ) as f:
            mock_content = f.read()
            mock_response.content = mock_content
    elif "files" in url:
        with open(
            DATA_DIR / "inspire_file.bin",
            "rb",
        ) as f:
            mock_content = f.read()
            mock_response.content = mock_content
    else:
        mock_response.json.return_value = mock_content
    return mock_response


def mock_head(url, allow_redirects=True):
    """Mock head request."""
    response = Mock()
    response.url = url
    return response


def legacy_entry(*cds_ids):
    """Build a minimal transformed entry with legacy CDS identifier(s)."""
    cds_ids = cds_ids or ("111",)
    return StreamEntry(
        {
            "id": "111",
            "metadata": {
                "title": "Test",
                "resource_type": {"id": "publication-article"},
                "identifiers": [
                    {"scheme": "cds", "identifier": cds_id} for cds_id in cds_ids
                ],
            },
            "files": {"enabled": False},
            "parent": {"access": {"owned_by": {"user": 2}}},
            "access": {"record": "public", "files": "public"},
            "_inspire_ctx": {"cds_id": cds_ids[0], "versions": []},
        }
    )


def add_legacy_recid(add_pid, record, recid):
    """Mint lrecid on the record parent (same as tests/legacy/test_redirector.py)."""
    parent = record._record.parent
    parent_pid = PersistentIdentifier.query.filter_by(
        pid_value=parent.pid.pid_value, pid_type="recid"
    ).one()
    add_pid(
        pid_type="lrecid",
        pid_value=str(recid),
        object_uuid=parent_pid.object_uuid,
    )


def run_harvester_mock(datastream_cfg, mock_content_function):
    """Process datastream."""
    legacy_cds_response = Mock(status_code=200)
    legacy_cds_response.headers = {}
    with (
        patch(
            "cds_rdm.inspire_harvester.reader.requests.get",
            side_effect=mock_content_function,
        ) as mock1,
        patch(
            "cds_rdm.inspire_harvester.load.files.requests.get",
            side_effect=mock_content_function,
        ) as mock2,
        patch(
            "cds_rdm.inspire_harvester.load.files.requests.head",
            side_effect=mock_head,
        ) as mock3,
        patch(
            "cds_rdm.inspire_harvester.load.matcher.RecordMatcher._get_legacy_cds",
            return_value=legacy_cds_response,
        ),
    ):
        process_datastream(config=datastream_cfg["config"])
        tasks = current_app.control.inspect()

        while True:
            if not tasks.scheduled():
                break
