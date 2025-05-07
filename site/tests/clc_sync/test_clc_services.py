import pytest
from invenio_access.permissions import system_identity

from cds_rdm.clc_sync.proxies import current_clc_sync_service
from cds_rdm.clc_sync.services.errors import CLCSyncAlreadyExistsError


@pytest.fixture()
def valid_data():
    return {
        "parent_record_pid": "test123",
        "clc_record_pid": "test123",
        "status": "S",
        "auto_sync": True,
    }


@pytest.fixture()
def valid_data2():
    return {
        "parent_record_pid": "xxxyyy",
        "clc_record_pid": "yyyxxx",
        "status": "F",
        "auto_sync": False,
    }


def test_create_and_read(app, db, valid_data):
    result = current_clc_sync_service.create(system_identity, valid_data)
    assert result.data["parent_record_pid"] == valid_data["parent_record_pid"]

    read_result = current_clc_sync_service.read(
        system_identity, valid_data["parent_record_pid"]
    )
    assert read_result.data["clc_record_pid"] == valid_data["clc_record_pid"]


def test_duplicate_create_raises(app, valid_data):
    current_clc_sync_service.create(system_identity, valid_data)
    with pytest.raises(CLCSyncAlreadyExistsError):
        current_clc_sync_service.create(system_identity, valid_data)


def test_update(app, valid_data2):
    created_data = current_clc_sync_service.create(system_identity, valid_data2)
    updated_data = {**valid_data2, "clc_record_pid": "clc789"}
    result = current_clc_sync_service.update(
        system_identity, created_data["id"], updated_data
    )
    assert result.data["clc_record_pid"] == "clc789"


def test_delete(app, valid_data):
    read_result = current_clc_sync_service.read(
        system_identity, valid_data["parent_record_pid"]
    )
    result = current_clc_sync_service.delete(system_identity, read_result["id"])
    assert result.data["parent_record_pid"] == valid_data["parent_record_pid"]
