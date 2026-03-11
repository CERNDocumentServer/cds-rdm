import json
from functools import partial
from io import BytesIO
from pathlib import Path
from time import sleep
from unittest.mock import Mock, patch

import pytest
from celery import current_app
from invenio_access.permissions import system_identity
from invenio_rdm_records.proxies import current_rdm_records_service
from invenio_rdm_records.records import RDMRecord
from invenio_search.engine import dsl
from invenio_vocabularies.services.tasks import process_datastream

from cds_rdm.legacy.resolver import get_record_by_version

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
            "resource_type": created_record["metadata"]["resource_type"],
        }
    ]
    assert created_record["metadata"]["identifiers"] == [
        {"scheme": "cds", "identifier": "2946564"}
    ]
    assert created_record["pids"]["doi"] == {
        "identifier": "10.1051/epjconf/202533701165",
        "provider": "external",
    }


def test_CDS_DOI_create_record_fails(
        running_app, location, scientific_community, datastream_config
):
    """Test insert record with CDS DOI - no record matched (deleted?)."""
    with open(
            DATA_DIR / "record_with_cds_DOI.json",
            "r",
    ) as f:
        new_record = json.load(f)

    mock_record = partial(mock_requests_get, mock_content=new_record)
    run_harvester_mock(datastream_config, mock_record)
    RDMRecord.index.refresh()

    doi_filters = [
        dsl.Q("term", **{"pids.doi": "10.17181/CERN.LELX.5VJY"}),
    ]
    filter = dsl.Q("bool", filter=doi_filters)

    created_records = current_rdm_records_service.search(
        system_identity, extra_filter=filter
    )
    assert created_records.total == 0


def test_update_record_with_CDS_DOI_one_doc_type(
        running_app,
        location,
        scientific_community,
        minimal_record_with_files,
        datastream_config,
):
    """Test update record with CDS DOI - matched record.

    Should create new version of record with article resource type.
    """

    # set this to emulate DOI creation
    running_app.app.config["RDM_PERSISTENT_IDENTIFIERS"]["doi"]["required"] = True
    minimal_record_with_files["metadata"]["publication_date"] = "2018"
    draft = current_rdm_records_service.create(
        system_identity, minimal_record_with_files
    )

    service = current_rdm_records_service
    add_file_to_draft(service.draft_files, system_identity, draft, "test")
    record = current_rdm_records_service.publish(system_identity, draft.id)

    with open(
            DATA_DIR / "record_with_cds_DOI.json",
            "r",
    ) as f:
        new_record = json.load(f)
        new_record["hits"]["hits"][0]["metadata"]["dois"] = [
            {"value": record["pids"]["doi"]["identifier"]}
        ]

    mock_record = partial(mock_requests_get, mock_content=new_record)
    RDMRecord.index.refresh()
    run_harvester_mock(datastream_config, mock_record)
    RDMRecord.index.refresh()

    doi_filters = [
        dsl.Q(
            "term",
            **{"pids.doi.identifier.keyword": record["pids"]["doi"]["identifier"]},
        ),
    ]
    filter = dsl.Q("bool", filter=doi_filters)

    created_records = current_rdm_records_service.search(
        system_identity, params={"allversions": True}, extra_filter=filter
    )

    assert created_records.total == 1

    original_record = current_rdm_records_service.read(system_identity, record["id"])
    assert original_record._record.versions.latest_index == 2
    new_version = get_record_by_version(original_record.data["parent"]["id"], 2)
    assert new_version.data["metadata"]["resource_type"]["id"] == "publication-preprint"
    assert new_version.data["metadata"]["publication_date"] == "2018"
    assert new_version.data["metadata"]["title"] == "Upgrade Software and Computing"
    assert {
               "identifier": "2707794",
               "scheme": "inspire",
               "relation_type": {"id": "isvariantformof"},
               "resource_type": {"id": "publication-preprint"},
           } in new_version.data["metadata"]["related_identifiers"]

    # clean up for other tests
    running_app.app.config["RDM_PERSISTENT_IDENTIFIERS"]["doi"]["required"] = False


def test_update_record_with_CDS_DOI_multiple_doc_types(
        running_app, location, scientific_community, existing_fcc_record,
        datastream_config,
):
    """Test update record with CDS DOI - matched record with multiple document types.

    The incoming INSPIRE record has document_type ["article", "report"] and files
    from two distinct sources (Springer + arXiv).  Because files differ from the
    existing record AND the record has a CDS DOI, the record must be split into
    as many new versions as there are document types (2).

    Splitting rules:
    - DOIs:       arXiv-sourced preprint DOI  → preprint version (datacite provider)
                  non-arXiv (Springer) DOI    → journalarticle version (external provider)
    - Titles:     source "arXiv"   → preprint version
                  source "Springer" → journalarticle version
    - Abstracts:  same source-based assignment as titles
    - Files:      arXiv document   → preprint version
                  Springer document → journalarticle version
    """
    # Enable DOI minting so the initial record receives a CDS DOI
    running_app.app.config["RDM_PERSISTENT_IDENTIFIERS"]["doi"]["required"] = True
    draft = current_rdm_records_service.create(system_identity, existing_fcc_record)
    with open(DATA_DIR / "b2snunu-11.pdf", "rb") as f:
        content = BytesIO(f.read())
    add_file_to_draft(current_rdm_records_service.draft_files, system_identity, draft,
                      "test", content=content)
    record = current_rdm_records_service.publish(system_identity, draft.id)
    cds_doi = record["pids"]["doi"]["identifier"]

    with open(
            DATA_DIR / "record_CDS_DOI_multiple_doc_types_2700388.json",
            "r",
    ) as f:
        inspire_record = json.load(f)

    # originally was { "value": "fp18d-jc149", "schema": "CDSRDM" } but we mock for test
    inspire_record["metadata"]["external_system_identifiers"].append(
        {"value": record._record.parent.pid.pid_value,
         "schema": "CDSRDM"})

    new_record = {"hits": {"total": 1, "hits": [inspire_record]}}

    mock_record = partial(mock_requests_get, mock_content=new_record)
    RDMRecord.index.refresh()
    run_harvester_mock(datastream_config, mock_record)
    RDMRecord.index.refresh()

    original_record = current_rdm_records_service.read(system_identity, record["id"])

    # 1. Record must be split into as many new versions as document_types
    #    ["article", "report"] → 2 new versions on top of the original → latest_index == 3
    # original was just text
    assert original_record._record.versions.latest_index == 3

    parent_id = original_record.data["parent"]["id"]
    v2 = get_record_by_version(parent_id, 2)
    v3 = get_record_by_version(parent_id, 3)

    assert v2.data["metadata"]["resource_type"]["id"] == "publication-report"
    assert v3.data["metadata"]["resource_type"]["id"] == "publication-article"

    report_v = v2
    article_v = v3

    assert article_v["pids"]["doi"]["identifier"] == "10.1007/JHEP01(2024)144"
    assert article_v["pids"]["doi"]["provider"] == "external"

    assert report_v["pids"]["doi"]["provider"] == "datacite"
    assert report_v["pids"]["doi"]["identifier"] == cds_doi

    # Titles are assigned per source:
    #    source "arXiv"    → report version
    #    source "Springer" → journalarticle version
    #    (source "CDS" would stay on the existing record — not present in this record)
    arxiv_title = r"Prospects for searches of $b \to s \nu \bar{\nu}$ decays at FCC-ee"
    springer_title = (
        r"Prospects for searches of $ b\to s\nu \overline{\nu} $ decays at FCC-ee"
    )
    assert report_v["metadata"]["title"] == arxiv_title
    assert article_v["metadata"]["title"] == springer_title

    # Other sourced fields follow the same source-based assignment:
    #    Abstracts — source "arXiv" → preprint, source "Springer" → journalarticle
    arxiv_abstract_fragment = r"b \to s \nu \bar{\nu}"
    springer_abstract_fragment = r"b\to s\nu \overline{\nu}"
    assert arxiv_abstract_fragment in report_v["metadata"]["description"]
    assert springer_abstract_fragment in article_v["metadata"]["description"]

    # Both versions must carry the INSPIRE related identifier
    for version in [article_v, report_v]:
        assert {
                   "scheme": "inspire",
                   "identifier": "2700388",
                   "relation_type": {"id": "isvariantformof"},
                   "resource_type": {"id": "publication-other"},
               } in version["metadata"]["related_identifiers"]

    # clean up for other tests
    running_app.app.config["RDM_PERSISTENT_IDENTIFIERS"]["doi"]["required"] = False


def test_update_migrated_record_with_CDS_DOI(
        running_app, location, scientific_community
):
    """Test update record with CDS DOI - should raise exception to handle manually."""
    passed = False


def test_update_no_CDS_DOI_one_doc_type(running_app, location, scientific_community):
    """Test update migrated record without CDS DOI - no record matched."""
    passed = False


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
            record.data["metadata"]["resource_type"][
                "id"] == "publication-conferencepaper"
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


@pytest.mark.skip(reason="metadata only to files transformation is broken")
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
            record.data["metadata"]["resource_type"][
                "id"] == "publication-conferencepaper"
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
