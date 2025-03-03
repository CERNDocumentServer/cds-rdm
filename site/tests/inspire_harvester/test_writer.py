# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""ISNPIRE harvester writer tests."""
from unittest.mock import Mock, patch

import pytest
from invenio_access.permissions import system_identity
from invenio_rdm_records.proxies import current_rdm_records, current_rdm_records_service
from invenio_vocabularies.datastreams import StreamEntry
from invenio_vocabularies.datastreams.errors import WriterError

from cds_rdm.inspire_harvester.writer import InspireWriter


def _cleanup_record(recid):
    """Delete a record after each test."""
    current_rdm_records.records_service.delete(system_identity, recid)


@pytest.fixture()
def transformed_record_1_file():
    """Transformed via InspireJsonTransformer record with 1 file."""
    return {
        "metadata": {
            "title": "Study of b- and c- jets identification for Higgs coupling measurement at muon collider",
            "publication_date": "2020",
            "resource_type": {"id": "publication-thesis"},
            "creators": [
                {
                    "person_or_org": {
                        "type": "personal",
                        "family_name": "Da Molin, Giacomo",
                    }
                }
            ],
            "identifiers": [{"identifier": "2685275", "scheme": "inspire"}],
        },
        "files": {
            "entries": {
                "fulltext.pdf": {
                    "checksum": "4c993d7ec1c1faf3c8e3a290219de361",
                    "key": "fulltext.pdf",
                    "access": {"hidden": False},
                    "inspire_url": "https://inspirehep.net/files/4c993d7ec1c1faf3c8e3a290219de361",
                }
            }
        },
        "parent": {"access": {"owned_by": {"user": 2}}},
        "access": {"record": "public", "files": "public"},
    }


@pytest.fixture()
def transformed_record_2_files():
    """Transformed via InspireJsonTransformer record with 2 files."""
    return {
        "metadata": {
            "title": "Study of b- and c- jets identification for Higgs coupling measurement at muon collider",
            "publication_date": "2020",
            "resource_type": {"id": "publication-thesis"},
            "creators": [
                {
                    "person_or_org": {
                        "type": "personal",
                        "family_name": "Da Molin, Giacomo",
                    }
                }
            ],
            "identifiers": [{"identifier": "2685275", "scheme": "inspire"}],
        },
        "files": {
            "entries": {
                "fulltext.pdf": {
                    "checksum": "4c993d7ec1c1faf3c8e3a290219de361",
                    "key": "fulltext.pdf",
                    "access": {"hidden": False},
                    "inspire_url": "https://inspirehep.net/files/4c993d7ec1c1faf3c8e3a290219de361",
                },
                "Afiq_Anuar_PhD_v3_DESY-THESIS.pdf": {
                    "checksum": "f45abb6d082da30cb6ee7e828454c680",
                    "key": "Afiq_Anuar_PhD_v3_DESY-THESIS.pdf",
                    "access": {"hidden": False},
                    "inspire_url": "https://inspirehep.net/files/f45abb6d082da30cb6ee7e828454c680",
                },
            }
        },
        "parent": {"access": {"owned_by": {"user": 2}}},
        "access": {"record": "public", "files": "public"},
    }


@pytest.fixture()
def transformed_record_no_files():
    """Transformed via InspireJsonTransformer record with no files."""
    return {
        "metadata": {
            "title": "Helium II heat transfer in LHC magnets",
            "additional_titles": [
                {"title": "Polyimide cable insulation", "type": {"id": "subtitle"}}
            ],
            "publication_date": "2017",
            "resource_type": {"id": "publication-thesis"},
            "creators": [
                {"person_or_org": {"type": "personal", "family_name": "Hanks, Tom"}},
                {"person_or_org": {"type": "personal", "family_name": "Potter, Harry"}},
                {"person_or_org": {"type": "personal", "family_name": "Weasley, Ron"}},
            ],
            "identifiers": [{"identifier": "1695540", "scheme": "inspire"}],
        },
        "files": {"enabled": False},
        "parent": {"access": {"owned_by": {"user": 2}}},
        "access": {"record": "public", "files": "public"},
    }


def test_writer_1_rec_no_files(running_app, location, transformed_record_no_files):
    """Test create a new metadata-only record."""
    writer = InspireWriter()

    # call writer
    writer.write_many([StreamEntry(transformed_record_no_files)])

    # assert that new record is created and published
    created_records = current_rdm_records_service.search(
        system_identity,
        params={
            "q": f"metadata.title:{transformed_record_no_files['metadata']['title']}"
        },
    )
    assert created_records.total == 1
    assert created_records.to_dict()["hits"]["hits"][0]["status"] == "published"
    assert created_records.to_dict()["hits"]["hits"][0]["files"]["enabled"] is False

    _cleanup_record(created_records.to_dict()["hits"]["hits"][0]["id"])


def test_writer_1_rec_1_file(running_app, location, transformed_record_1_file):
    """Test create a new record with 1 file."""
    writer = InspireWriter()

    # call writer
    writer.write_many([StreamEntry(transformed_record_1_file)])

    # assert that new record is created and published
    created_records = current_rdm_records_service.search(
        system_identity,
        params={
            "q": f"metadata.title:{transformed_record_1_file['metadata']['title']}"
        },
    )
    assert created_records.total == 1

    record = created_records.to_dict()["hits"]["hits"][0]
    assert record["status"] == "published"

    # check files
    files = record["files"]
    assert files["enabled"] is True
    assert files["count"] == 1
    assert "fulltext.pdf" in files["entries"]
    assert (
        files["entries"]["fulltext.pdf"]["checksum"]
        == "md5:"
        + transformed_record_1_file["files"]["entries"]["fulltext.pdf"]["checksum"]
    )
    assert files["entries"]["fulltext.pdf"]["ext"] == "pdf"
    assert files["entries"]["fulltext.pdf"]["mimetype"] == "application/pdf"
    assert (
        files["entries"]["fulltext.pdf"]["key"]
        == transformed_record_1_file["files"]["entries"]["fulltext.pdf"]["key"]
    )

    # check that we removed inspire_url
    assert "inspire_url" not in files["entries"]["fulltext.pdf"]

    _cleanup_record(record["id"])


def test_writer_1_rec_1_file_failed(
    running_app, location, caplog, transformed_record_1_file
):
    """Test create a new record with 1 file. File upload failed."""
    writer = InspireWriter()
    transformed_record = transformed_record_1_file

    # make url invalid
    transformed_record["files"]["entries"]["fulltext.pdf"]["checksum"] = "fake"
    transformed_record["files"]["entries"]["fulltext.pdf"][
        "inspire_url"
    ] = "https://inspirehep.net/files/fake"

    # call writer
    writer.write_many([StreamEntry(transformed_record)])

    # check that stuff was logged
    assert (
        "Retrieving file request failed on attempt 1. Max retries: 3. Status: 404"
        in caplog.text
    )
    assert "URL: https://inspirehep.net/files/fake" in caplog.text
    assert "Filename: fulltext.pdf. INSPIRE record id: 2685275." in caplog.text
    assert "Retrying in 1 minute..." in caplog.text

    # assert that no record was created
    created_records = current_rdm_records_service.search(
        system_identity,
        params={"q": f"metadata.title:{transformed_record['metadata']['title']}"},
    )

    assert created_records.total == 0


def test_writer_2_records(running_app, location, transformed_record_1_file):
    """Test create 2 new records."""
    writer = InspireWriter()

    transformed_record2 = {
        "metadata": {
            "title": "The effect of hadronization on the $\\phi$* distribution of the Z boson in simulation compared to data from the CMS experiment at $\\sqrt{s}$ = 8 Tev",
            "publication_date": "2019",
            "resource_type": {"id": "publication-thesis"},
            "creators": [
                {
                    "person_or_org": {
                        "type": "personal",
                        "family_name": "Lesko, Zachary John",
                    }
                }
            ],
            "identifiers": [{"identifier": "1793973", "scheme": "inspire"}],
        },
        "files": {
            "entries": {
                "fulltext.pdf": {
                    "checksum": "0b0532554c3864fa80e73f54df9b77c6",
                    "key": "fulltext.pdf",
                    "access": {"hidden": False},
                    "inspire_url": "https://inspirehep.net/files/0b0532554c3864fa80e73f54df9b77c6",
                }
            }
        },
        "parent": {"access": {"owned_by": {"user": 2}}},
        "access": {"record": "public", "files": "public"},
    }

    # call writer
    writer.write_many(
        [StreamEntry(transformed_record_1_file), StreamEntry(transformed_record2)]
    )

    # assert that 2 new records are created and published
    all_created_records = current_rdm_records_service.search(system_identity)
    assert all_created_records.total == 2

    record1 = all_created_records.to_dict()["hits"]["hits"][0]
    record2 = all_created_records.to_dict()["hits"]["hits"][1]

    assert record1["status"] == "published"
    assert record2["status"] == "published"
    assert record1["metadata"]["title"] == transformed_record2["metadata"]["title"]
    assert (
        record2["metadata"]["title"] == transformed_record_1_file["metadata"]["title"]
    )

    # check files
    files1 = record1["files"]
    assert files1["enabled"] is True
    assert files1["count"] == 1
    assert "fulltext.pdf" in files1["entries"]
    assert (
        files1["entries"]["fulltext.pdf"]["checksum"]
        == "md5:" + transformed_record2["files"]["entries"]["fulltext.pdf"]["checksum"]
    )
    assert files1["entries"]["fulltext.pdf"]["ext"] == "pdf"
    assert files1["entries"]["fulltext.pdf"]["mimetype"] == "application/pdf"
    assert (
        files1["entries"]["fulltext.pdf"]["key"]
        == transformed_record2["files"]["entries"]["fulltext.pdf"]["key"]
    )

    files2 = record2["files"]
    assert files2["enabled"] is True
    assert files2["count"] == 1
    assert "fulltext.pdf" in files2["entries"]
    assert (
        files2["entries"]["fulltext.pdf"]["checksum"]
        == "md5:"
        + transformed_record_1_file["files"]["entries"]["fulltext.pdf"]["checksum"]
    )
    assert files2["entries"]["fulltext.pdf"]["ext"] == "pdf"
    assert files2["entries"]["fulltext.pdf"]["mimetype"] == "application/pdf"
    assert (
        files2["entries"]["fulltext.pdf"]["key"]
        == transformed_record_1_file["files"]["entries"]["fulltext.pdf"]["key"]
    )

    _cleanup_record(record1["id"])
    _cleanup_record(record2["id"])


def test_writer_2_existing_found(running_app, location, transformed_record_no_files):
    """Test got 2 existing records."""
    writer = InspireWriter()

    draft = current_rdm_records_service.create(
        system_identity, transformed_record_no_files
    )
    current_rdm_records_service.publish(system_identity, draft.id)

    draft2 = current_rdm_records_service.create(
        system_identity, transformed_record_no_files
    )
    current_rdm_records_service.publish(system_identity, draft2.id)

    # call writer
    with pytest.raises(WriterError) as e:
        writer.write_many([StreamEntry(transformed_record_no_files)])
    assert (
        str(e.value)
        == f"More than 1 record found with INSPIRE id 1695540. CDS records found: {draft.id}, {draft2.id}"
    )

    _cleanup_record(draft.id)
    _cleanup_record(draft2.id)


def test_writer_1_existing_found_metadata_changes_no_files(
    running_app, location, transformed_record_no_files
):
    """Test got 1 existing record, only metadata changes needed, no files present."""
    writer = InspireWriter()
    transformed_record = transformed_record_no_files

    # create a record
    draft = current_rdm_records_service.create(system_identity, transformed_record)
    current_rdm_records_service.publish(system_identity, draft.id)

    # make changes to metadata
    transformed_record["metadata"]["title"] = "Another title"
    transformed_record["metadata"]["publication_date"] = "2025"

    # call writer
    writer.write_many([StreamEntry(transformed_record)])

    # assert there is no record with an old title
    created_records = current_rdm_records_service.search(
        system_identity,
        params={"q": f"metadata.title:Helium II heat transfer in LHC magnets"},
    )
    assert created_records.total == 0

    # assert the existing record has new title and new publication_date
    existing_record = current_rdm_records_service.read(
        system_identity, draft.id
    ).to_dict()
    assert existing_record["metadata"]["title"] == "Another title"
    assert existing_record["metadata"]["publication_date"] == "2025"

    # assert that this record is still v1
    existing_record["versions"]["index"] == 1

    _cleanup_record(draft.id)


def test_writer_1_existing_found_files_not_changed_metadata_changed(
    running_app, location, transformed_record_1_file
):
    """Test got 1 existing record, files stayed the same, metadata changed."""
    writer = InspireWriter()
    transformed_record = transformed_record_1_file

    # creates a record
    writer.write_many([StreamEntry(transformed_record)])

    # make changes to metadata
    transformed_record["metadata"]["title"] = "Another title"
    transformed_record["metadata"]["publication_date"] = "2025"

    # call writer
    writer.write_many([StreamEntry(transformed_record)])

    # assert there is no record with an old title
    created_records = current_rdm_records_service.search(
        system_identity,
        params={
            "q": f"metadata.title:Study of b- and c- jets identification for Higgs coupling measurement at muon collider"
        },
    )
    assert created_records.total == 0

    # assert the existing record has new title and new publication_date
    existing_records = current_rdm_records_service.search(
        system_identity,
        params={"q": f"metadata.title:Another title"},
    )
    existing = existing_records.to_dict()["hits"]["hits"][0]
    assert existing["metadata"]["publication_date"] == "2025"

    # assert that file didn't change
    assert len(existing["files"]["entries"]) == 1
    assert "fulltext.pdf" in existing["files"]["entries"]
    assert (
        existing["files"]["entries"]["fulltext.pdf"]["checksum"]
        == "md5:4c993d7ec1c1faf3c8e3a290219de361"
    )
    assert existing["files"]["entries"]["fulltext.pdf"]["key"] == "fulltext.pdf"

    # assert that this record is still v1
    existing["versions"]["index"] == 1

    _cleanup_record(existing["id"])


def test_writer_1_existing_found_file_changed_new_version_created(
    running_app, location, transformed_record_1_file
):
    """Test got 1 existing record, only metadata stayed the same, files changed. New version was created."""
    writer = InspireWriter()
    transformed_record = transformed_record_1_file

    # creates a record
    writer.write_many([StreamEntry(transformed_record)])

    # make changes to files
    transformed_record["files"]["entries"]["fulltext.pdf"] = {
        "checksum": "f45abb6d082da30cb6ee7e828454c680",
        "key": "Afiq_Anuar_PhD_v3_DESY-THESIS.pdf",
        "access": {"hidden": False},
        "inspire_url": "https://inspirehep.net/files/f45abb6d082da30cb6ee7e828454c680",
    }

    # call writer
    writer.write_many([StreamEntry(transformed_record)])

    # assert that only 1 rec exists with this title
    created_records = current_rdm_records_service.search(
        system_identity,
        params={"q": f"metadata.title:{transformed_record['metadata']['title']}"},
    )
    assert created_records.total == 1

    # assert that record still has only 1 file and it's the new one
    files = created_records.to_dict()["hits"]["hits"][0]["files"]
    assert len(files["entries"]) == 1
    assert "Afiq_Anuar_PhD_v3_DESY-THESIS.pdf" in files["entries"]
    assert (
        files["entries"]["Afiq_Anuar_PhD_v3_DESY-THESIS.pdf"]["checksum"]
        == "md5:f45abb6d082da30cb6ee7e828454c680"
    )
    assert (
        files["entries"]["Afiq_Anuar_PhD_v3_DESY-THESIS.pdf"]["key"]
        == "Afiq_Anuar_PhD_v3_DESY-THESIS.pdf"
    )

    # assert that this record is v2
    created_records.to_dict()["hits"]["hits"][0]["versions"]["index"] == 2

    _cleanup_record(created_records.to_dict()["hits"]["hits"][0]["id"])


def test_writer_1_existing_found_file_and_metadata_changed(
    running_app, location, transformed_record_1_file
):
    """Test got 1 existing record, both metadata and file changed. New version created."""
    writer = InspireWriter()
    transformed_record = transformed_record_1_file

    # creates a record
    writer.write_many([StreamEntry(transformed_record)])

    # make changes to files
    transformed_record["files"]["entries"]["fulltext.pdf"] = {
        "checksum": "f45abb6d082da30cb6ee7e828454c680",
        "key": "Afiq_Anuar_PhD_v3_DESY-THESIS.pdf",
        "access": {"hidden": False},
        "inspire_url": "https://inspirehep.net/files/f45abb6d082da30cb6ee7e828454c680",
    }

    # make changes to metadata
    transformed_record["metadata"]["title"] = "Another title"
    transformed_record["metadata"]["publication_date"] = "2025"

    # call writer
    writer.write_many([StreamEntry(transformed_record)])

    # assert that only 1 rec exists with this title
    created_records = current_rdm_records_service.search(
        system_identity,
        params={"q": f"metadata.title:{transformed_record['metadata']['title']}"},
    )
    assert created_records.total == 1

    # assert that metadata changed
    record = created_records.to_dict()["hits"]["hits"][0]
    assert record["metadata"]["publication_date"] == "2025"

    # assert that record still has only 1 file and it's the new one
    files = record["files"]
    assert len(files["entries"]) == 1
    assert "Afiq_Anuar_PhD_v3_DESY-THESIS.pdf" in files["entries"]
    assert (
        files["entries"]["Afiq_Anuar_PhD_v3_DESY-THESIS.pdf"]["checksum"]
        == "md5:f45abb6d082da30cb6ee7e828454c680"
    )
    assert (
        files["entries"]["Afiq_Anuar_PhD_v3_DESY-THESIS.pdf"]["key"]
        == "Afiq_Anuar_PhD_v3_DESY-THESIS.pdf"
    )

    # assert that this record is v2
    created_records.to_dict()["hits"]["hits"][0]["versions"]["index"] == 2

    _cleanup_record(record["id"])


def test_writer_1_existing_found_1_more_file_added(
    running_app, location, transformed_record_1_file
):
    """Test got 1 existing record, 1 file matched the existing, 1 more file was added. New version created."""
    writer = InspireWriter()
    transformed_record = transformed_record_1_file

    # creates a record
    writer.write_many([StreamEntry(transformed_record)])

    # add one more file
    transformed_record["files"]["entries"]["Afiq_Anuar_PhD_v3_DESY-THESIS.pdf"] = {
        "checksum": "f45abb6d082da30cb6ee7e828454c680",
        "key": "Afiq_Anuar_PhD_v3_DESY-THESIS.pdf",
        "access": {"hidden": False},
        "inspire_url": "https://inspirehep.net/files/f45abb6d082da30cb6ee7e828454c680",
    }

    # call writer
    writer.write_many([StreamEntry(transformed_record)])

    # assert that only 1 rec exists with this title
    created_records = current_rdm_records_service.search(
        system_identity,
        params={"q": f"metadata.title:{transformed_record['metadata']['title']}"},
    )
    assert created_records.total == 1

    # assert that record has now 2 files
    files = created_records.to_dict()["hits"]["hits"][0]["files"]
    assert len(files["entries"]) == 2

    # the new one
    assert "Afiq_Anuar_PhD_v3_DESY-THESIS.pdf" in files["entries"]
    assert (
        files["entries"]["Afiq_Anuar_PhD_v3_DESY-THESIS.pdf"]["checksum"]
        == "md5:f45abb6d082da30cb6ee7e828454c680"
    )
    assert (
        files["entries"]["Afiq_Anuar_PhD_v3_DESY-THESIS.pdf"]["key"]
        == "Afiq_Anuar_PhD_v3_DESY-THESIS.pdf"
    )

    # and the old one
    assert "fulltext.pdf" in files["entries"]
    assert (
        files["entries"]["fulltext.pdf"]["checksum"]
        == "md5:4c993d7ec1c1faf3c8e3a290219de361"
    )
    assert files["entries"]["fulltext.pdf"]["key"] == "fulltext.pdf"

    # assert that this record is v2
    created_records.to_dict()["hits"]["hits"][0]["versions"]["index"] == 2

    _cleanup_record(created_records.to_dict()["hits"]["hits"][0]["id"])


def test_writer_1_existing_found_with_2_files_1_deleted(
    running_app, location, transformed_record_2_files
):
    """Test got 1 existing record that had 2 files. Only 1 of them came from INSPIRE, the other one is deleted. New version created."""
    writer = InspireWriter()
    transformed_record = transformed_record_2_files

    # creates a record
    writer.write_many([StreamEntry(transformed_record)])

    # remove 1 file
    del transformed_record["files"]["entries"]["Afiq_Anuar_PhD_v3_DESY-THESIS.pdf"]

    # call writer
    writer.write_many([StreamEntry(transformed_record)])

    created_records = current_rdm_records_service.search(
        system_identity,
        params={"q": f"metadata.title:{transformed_record['metadata']['title']}"},
    )

    # assert that record has now only 1 file
    files = created_records.to_dict()["hits"]["hits"][0]["files"]
    assert len(files["entries"]) == 1
    assert "fulltext.pdf" in files["entries"]
    assert (
        files["entries"]["fulltext.pdf"]["checksum"]
        == "md5:4c993d7ec1c1faf3c8e3a290219de361"
    )
    assert files["entries"]["fulltext.pdf"]["key"] == "fulltext.pdf"

    # assert that this record is v2
    created_records.to_dict()["hits"]["hits"][0]["versions"]["index"] == 2

    _cleanup_record(created_records.to_dict()["hits"]["hits"][0]["id"])


def test_writer_1_existing_found_with_2_files_1_deleted_1_added(
    running_app, location, transformed_record_2_files
):
    """Test got 1 existing record that had 2 files. From INSPIRE came 1 old file and 1 new file. Files were replaced. New version created."""
    writer = InspireWriter()
    transformed_record = transformed_record_2_files

    # creates a record
    writer.write_many([StreamEntry(transformed_record)])

    # remove 1 file and add another one
    del transformed_record["files"]["entries"]["Afiq_Anuar_PhD_v3_DESY-THESIS.pdf"]
    transformed_record["files"]["entries"]["Maier.pdf"] = {
        "checksum": "0f9dd913d49cf6bf2413b2310088bed6",
        "key": "Maier.pdf",
        "access": {"hidden": False},
        "inspire_url": "https://inspirehep.net/files/0f9dd913d49cf6bf2413b2310088bed6",
    }

    # call writer
    writer.write_many([StreamEntry(transformed_record)])

    created_records = current_rdm_records_service.search(
        system_identity,
        params={"q": f"metadata.title:{transformed_record['metadata']['title']}"},
    )

    # assert that record has 2 files and it's 1 old and 1 new
    files = created_records.to_dict()["hits"]["hits"][0]["files"]
    assert len(files["entries"]) == 2
    assert "fulltext.pdf" in files["entries"]
    assert (
        files["entries"]["fulltext.pdf"]["checksum"]
        == "md5:4c993d7ec1c1faf3c8e3a290219de361"
    )
    assert files["entries"]["fulltext.pdf"]["key"] == "fulltext.pdf"

    assert "Maier.pdf" in files["entries"]
    assert (
        files["entries"]["Maier.pdf"]["checksum"]
        == "md5:0f9dd913d49cf6bf2413b2310088bed6"
    )
    assert files["entries"]["Maier.pdf"]["key"] == "Maier.pdf"

    # assert that the file Afiq_Anuar_PhD_v3_DESY-THESIS.pdf was deleted
    assert "Afiq_Anuar_PhD_v3_DESY-THESIS.pdf" not in files["entries"]

    # assert that this record is v2
    created_records.to_dict()["hits"]["hits"][0]["versions"]["index"] == 2

    _cleanup_record(created_records.to_dict()["hits"]["hits"][0]["id"])


def test_writer_1_existing_found_all_files_deleted(
    running_app, location, transformed_record_1_file
):
    """Test got 1 existing record. All it's files were deleted and now the record is metadata-only. New version created."""
    writer = InspireWriter()
    transformed_record = transformed_record_1_file

    # creates a record
    writer.write_many([StreamEntry(transformed_record)])

    # remove file
    transformed_record["files"] = {"enabled": False}

    # call writer
    writer.write_many([StreamEntry(transformed_record)])

    created_records = current_rdm_records_service.search(
        system_identity,
        params={"q": f"metadata.title:{transformed_record['metadata']['title']}"},
    )

    # assert that record has 0 files
    files = created_records.to_dict()["hits"]["hits"][0]["files"]
    assert len(files["entries"]) == 0

    # assert that record is metadata-only now
    assert files["enabled"] is False

    # assert that this record is v2
    created_records.to_dict()["hits"]["hits"][0]["versions"]["index"] == 2

    _cleanup_record(created_records.to_dict()["hits"]["hits"][0]["id"])


def test_writer_1_existing_found_1_file_added(
    running_app, location, transformed_record_no_files
):
    """Test got 1 existing record that was metadata-only. Added 1 file. New version created."""
    writer = InspireWriter()
    transformed_record = transformed_record_no_files

    # creates a record
    writer.write_many([StreamEntry(transformed_record)])

    # add a file
    transformed_record["files"] = {
        "entries": {
            "Maier.pdf": {
                "checksum": "0f9dd913d49cf6bf2413b2310088bed6",
                "key": "Maier.pdf",
                "access": {"hidden": False},
                "inspire_url": "https://inspirehep.net/files/0f9dd913d49cf6bf2413b2310088bed6",
            }
        }
    }

    # call writer
    writer.write_many([StreamEntry(transformed_record)])

    created_records = current_rdm_records_service.search(
        system_identity,
        params={"q": f"metadata.title:{transformed_record['metadata']['title']}"},
    )

    # assert that record has 1 file now
    files = created_records.to_dict()["hits"]["hits"][0]["files"]
    assert len(files["entries"]) == 1
    assert "Maier.pdf" in files["entries"]

    # assert that record is not metadata-only now
    assert files["enabled"] is True

    # assert that this record is v2
    created_records.to_dict()["hits"]["hits"][0]["versions"]["index"] == 2

    _cleanup_record(created_records.to_dict()["hits"]["hits"][0]["id"])


def test_writer_1_existing_found_new_version_creation_failed(
    running_app, location, transformed_record_1_file
):
    """Test failing of creation of new version."""
    writer = InspireWriter()
    transformed_record = transformed_record_1_file

    # creates a record
    writer.write_many([StreamEntry(transformed_record)])

    # make url invalid
    transformed_record["files"]["entries"]["fulltext.pdf"]["checksum"] = "fake"
    transformed_record["files"]["entries"]["fulltext.pdf"][
        "inspire_url"
    ] = "https://inspirehep.net/files/fake"

    # call writer
    writer.write_many([StreamEntry(transformed_record)])

    created_records = current_rdm_records_service.search(
        system_identity,
        params={
            "q": f"metadata.title:{transformed_record_1_file['metadata']['title']}"
        },
    )

    # assert that record still has the old file
    files = created_records.to_dict()["hits"]["hits"][0]["files"]
    assert len(files["entries"]) == 1
    assert "fulltext.pdf" in files["entries"]
    assert (
        files["entries"]["fulltext.pdf"]["checksum"]
        == "md5:4c993d7ec1c1faf3c8e3a290219de361"
    )

    # assert that this record is still v1
    created_records.to_dict()["hits"]["hits"][0]["versions"]["index"] == 1

    _cleanup_record(created_records.to_dict()["hits"]["hits"][0]["id"])
