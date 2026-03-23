# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

import json
from functools import partial
from pathlib import Path

from invenio_access.permissions import system_identity
from invenio_rdm_records.proxies import current_rdm_records_service
from invenio_rdm_records.records import RDMRecord

from ..conftest import minimal_record_with_files
from ..utils import add_file_to_draft
from .utils import mock_requests_get, run_harvester_mock

DATA_DIR = Path(__file__).parent / "data"


def test_new_non_CDS_record(
    running_app, location, scientific_community, datastream_config
):
    """Test new non-CDS origin record."""

    with open(
        DATA_DIR / "completely_new_inspire_rec.json",
        "r",
    ) as f:
        new_record = json.load(f)

    mock_record = partial(mock_requests_get, mock_content=new_record)
    run_harvester_mock(datastream_config, mock_record)

    RDMRecord.index.refresh()
    created_records = current_rdm_records_service.search(system_identity)
    assert created_records.total == 1
    created_record = created_records.to_dict()["hits"]["hits"][0]
    assert created_record["metadata"]["related_identifiers"] == [
        {
            "scheme": "inspire",
            "identifier": "3065322",
            "relation_type": {
                "id": "isvariantformof",
                "title": {
                    "en": "is variant of",
                },
            },
            "resource_type": {
                "id": "publication-conferencepaper",
                "title": {
                    "de": "Abschlussarbeit",
                    "en": "Thesis",
                },
            },
        }
    ]
    assert created_record["metadata"]["identifiers"] == [
        {"scheme": "cds", "identifier": "2946564"}
    ]
    assert created_record["pids"]["doi"] == {
        "identifier": "10.1051/epjconf/202533701165",
        "provider": "external",
    }


def test_update_no_CDS_DOI_multiple_doc_types(
    running_app,
    location,
    scientific_community,
    datastream_config,
    minimal_record_with_files,
):
    service = current_rdm_records_service

    minimal_record_with_files["metadata"]["resource_type"] = {
        "id": "publication-preprint"
    }
    minimal_record_with_files["metadata"]["related_identifiers"] = [
        {
            "identifier": "2104.13342",
            "scheme": "arxiv",
            "relation_type": {"id": "isversionof"},
            "resource_type": {"id": "publication-other"},
        }
    ]
    minimal_record_with_files["metadata"]["publication_date"] = "2021"

    draft = service.create(system_identity, minimal_record_with_files)
    add_file_to_draft(service.draft_files, system_identity, draft, "test")
    record = current_rdm_records_service.publish(system_identity, draft.id)

    RDMRecord.index.refresh()
    with open(
        DATA_DIR / "record_with_no_cds_DOI_multiple_doc_type.json",
        "r",
    ) as f:
        new_record = json.load(f)

    mock_record = partial(mock_requests_get, mock_content=new_record)
    RDMRecord.index.refresh()
    run_harvester_mock(datastream_config, mock_record)
    RDMRecord.index.refresh()

    record = current_rdm_records_service.read(system_identity, record["id"])
    assert (
        record.data["metadata"]["resource_type"]["id"] == "publication-conferencepaper"
    )
    # ensure we didn't create a new version
    assert record._record.versions.latest_index == 1
    # check title updated
    assert (
        record.data["metadata"]["title"]
        == "Search for pseudoscalar bosons decaying into $e^+e^-$ pairs in the NA64 experiment at the CERN SPS"
    )
    # check files replaced
    # when we manage non-CDS record - we trust INSPIRE as a source of truth
    # therefore files will be synced 1:1 with INSPIRE
    assert "PhysRevD.104.L111102.pdf" in record._record.files.entries
    assert len(record._record.files.entries.items()) == 1


