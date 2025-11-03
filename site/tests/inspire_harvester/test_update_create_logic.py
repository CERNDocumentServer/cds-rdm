import json
from functools import partial
from unittest.mock import Mock, patch

from celery import current_app
from invenio_access.permissions import system_identity
from invenio_rdm_records.proxies import current_rdm_records_service
from invenio_rdm_records.records import RDMRecord
from invenio_vocabularies.services.tasks import process_datastream

from .utils import mock_requests_get, run_harvester_mock


def test_new_non_CDS_record(
    running_app, location, scientific_community, datastream_config
):
    """Test new non-CDS origin record."""

    with open(
        "tests/inspire_harvester/data/completely_new_inspire_rec.json",
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
                "id": "isvariantof",
                "title": {
                    "en": "is variant of",
                },
            },
            "resource_type": {
                "id": "publication-other",
                "title": {
                    "de": "Abschlussarbeit",
                    "en": "Other",
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


def test_CDS_DOI_record_not_found(running_app, location, scientific_community):
    """Test insert record with CDS DOI - no record matched (deleted?)."""
    passed = False


def test_update_record_with_CDS_DOI(running_app, location, scientific_community):
    """Test update record with CDS DOI - no record matched."""
    passed = False


def test_update_migrated_record_with_CDS_DOI(
    running_app, location, scientific_community
):
    """Test update record with CDS DOI - should raise exception to handle manually."""
    passed = False


def test_update_no_CDS_DOI(running_app, location, scientific_community):
    """Test update migrated record without CDS DOI - no record matched."""
    passed = False
