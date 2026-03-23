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


def test_update_no_CDS_DOI_from_metadata_only_to_files(
    running_app, location, scientific_community, datastream_config, minimal_record
):
    """Test update record, originally no files, adding files to the same version."""
    service = current_rdm_records_service

    minimal_record["metadata"]["resource_type"] = {"id": "publication-preprint"}
    minimal_record["metadata"]["related_identifiers"] = [
        {
            "identifier": "2104.13345",
            "scheme": "arxiv",
            "relation_type": {"id": "isversionof"},
            "resource_type": {"id": "publication-other"},
        }
    ]
    minimal_record["metadata"]["publication_date"] = "2021"

    draft = service.create(system_identity, minimal_record)
    record = current_rdm_records_service.publish(system_identity, draft.id)

    RDMRecord.index.refresh()
    with open(
        DATA_DIR / "record_with_no_cds_DOI_multiple_doc_type2.json",
        "r",
    ) as f:
        new_record = json.load(f)

    mock_record = partial(mock_requests_get, mock_content=new_record)
    RDMRecord.index.refresh()
    run_harvester_mock(datastream_config, mock_record)
    RDMRecord.index.refresh()

    record = current_rdm_records_service.read(system_identity, record["id"])
    # from preprint to conference paper
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


