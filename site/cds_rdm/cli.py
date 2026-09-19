# -*- coding: utf-8 -*-
#
# Copyright (C) 2025-2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.


"""CDS-RDM CLI."""

import csv

import click
from flask.cli import with_appcontext
from invenio_access.permissions import system_identity
from invenio_communities.proxies import current_communities
from invenio_db import db
from invenio_pidstore.models import PersistentIdentifier
from invenio_rdm_records.proxies import current_rdm_records_service
from invenio_rdm_records.records.api import RDMDraft, RDMRecord
from invenio_rdm_records.records.models import (
    RDMDraftMetadata,
    RDMFileDraftMetadata,
    RDMFileRecordMetadata,
    RDMParentCommunity,
    RDMRecordMetadata,
    RDMVersionsState,
)
from invenio_requests.proxies import current_requests_service
from invenio_requests.records.api import Request
from invenio_requests.records.models import RequestMetadata


def _get_parent(record_model):
    parent_model = record_model.parent
    parent_id = str(parent_model.id)

    # Parent communities
    parent_communities_ids = [
        comm for comm in parent_model.json["communities"].get("ids", [])
    ]
    parent_communities = (
        RDMParentCommunity.query.filter(
            RDMParentCommunity.community_id.in_(parent_communities_ids)
        )
        .filter(RDMParentCommunity.record_id == parent_id)
        .all()
    )

    parent_pid = PersistentIdentifier.query.filter(
        PersistentIdentifier.pid_value == parent_model.json["id"]
    ).one()

    requests_ids = [comm.request_id for comm in parent_communities]
    requests = []
    if requests_ids:
        requests = Request.get_records(requests_ids)

    return (parent_model, parent_id, parent_pid, parent_communities, requests)


def _get_record(recid):
    # PID
    record_pid = PersistentIdentifier.query.filter(
        PersistentIdentifier.pid_value == recid
    ).one()
    record_id = str(record_pid.object_uuid)
    # Associated identifiers
    record_identifiers = [
        identifier
        for identifier in PersistentIdentifier.query.filter(
            PersistentIdentifier.object_uuid == record_id
        ).all()
        if identifier.pid_value != recid
    ]
    # Record
    record_model = RDMRecordMetadata.query.filter_by(id=record_id).one()
    rdm_record = RDMRecord.get_record(record_id)

    # Draft
    draft_model = RDMDraftMetadata.query.filter_by(id=record_id).one_or_none()
    rdm_draft = None
    if draft_model:
        rdm_draft = RDMDraft.get_record(record_id, with_deleted=True)

    return (
        record_pid,
        record_id,
        record_identifiers,
        record_model,
        rdm_record,
        draft_model,
        rdm_draft,
    )


def _get_version(recid, parent_id):
    record_version = RDMVersionsState.query.filter(
        RDMVersionsState.parent_id == parent_id
    ).one_or_none()
    # check how many versions exist
    all_versions = current_rdm_records_service.search_versions(
        system_identity,
        recid,
    ).to_dict()["hits"]

    latest_record_version_id = str(record_version.latest_id)

    return (record_version, latest_record_version_id, all_versions)


def _delete_files(record_id):
    # Delete files for the record
    record_files = RDMFileRecordMetadata.query.filter(
        RDMFileRecordMetadata.record_id == record_id
    ).all()
    draft_files = RDMFileDraftMetadata.query.filter(
        RDMFileDraftMetadata.record_id == record_id
    ).all()

    for _file in record_files + draft_files:
        db.session.delete(_file)


def _delete_identifiers(identifiers):
    # delete records identifiers e.g oai, doi
    for identifier in identifiers:
        db.session.delete(identifier)


def _cleanup_record(
    record_version,
    record_pid,
    record_model,
    draft_model,
    parent_model,
    parent_pid,
    parent_communities,
):
    # record is the last existing version
    db.session.delete(record_version)
    # delete record pid
    db.session.delete(record_pid)
    # delete record
    db.session.delete(record_model)
    # delete draft
    if draft_model:
        db.session.delete(draft_model)
    # delete parent record
    db.session.delete(parent_model)
    # delete parent pid
    db.session.delete(parent_pid)
    # delete a parent communities
    for comm in parent_communities:
        db.session.delete(comm)
        request_id = comm.request_id
        # use model here to take advantage of the cascade deletion of request events
        RequestMetadata.query.filter(RequestMetadata.id == request_id).delete()


def _delete_record_and_draft(record_pid, record_model, draft_model):
    # delete record pid
    db.session.delete(record_pid)
    db.session.delete(record_model)
    # delete draft
    if draft_model:
        db.session.delete(draft_model)


def _revert_record_to_previous_version(latest_version, all_versions):
    # record has previous versions, so let's revert to the previous one
    previous_record = all_versions["hits"][1]
    previous_record_pid = PersistentIdentifier.query.filter(
        PersistentIdentifier.pid_value == previous_record["id"]
    ).one()
    latest_version.latest_id = str(previous_record_pid.object_uuid)
    latest_version.latest_index = previous_record["versions"]["index"]
    db.session.add(latest_version)


@click.group()
def cds_admin():
    """CDS admin commands."""


@cds_admin.command("delete")
@click.option(
    "-r",
    "--recid",
    type=str,
    required=True,
    help="A command to delete a record by giving the pid to delete. This is a temporary solution until the deletion mechanism is implemented in service layer.",
)
@with_appcontext
def delete_record(recid):
    """Custom script to delete a record.

    A command to delete a record by giving the pid to delete. **This is a temporary solution** until the deletion mechanism is implemented in service layer.
    Usage: invenio cds-admin delete -r <recid>
    """
    # Record
    (
        record_pid,
        record_id,
        record_identifiers,
        record_model,
        rdm_record,
        draft_model,
        rdm_draft,
    ) = _get_record(recid)
    # Parent
    (parent_model, parent_id, parent_pid, parent_communities, requests) = _get_parent(
        record_model
    )
    # Version
    (record_version, latest_record_version_id, all_versions) = _get_version(
        recid, parent_id
    )

    with db.session.begin_nested():
        _delete_files(record_id)
        _delete_identifiers(record_identifiers)

        # Are we deleting the latest record version?
        if latest_record_version_id == record_id:
            if all_versions["total"] == 1:
                _cleanup_record(
                    record_version,
                    record_pid,
                    record_model,
                    draft_model,
                    parent_model,
                    parent_pid,
                    parent_communities,
                )
            else:
                # NOTE: the record versions index is not properly adjusted when you delete a record.
                # That means that records versions can have inconsistencies between them e.g version 1, version 3, version 7
                # if you delete intermediate records
                _revert_record_to_previous_version(record_version, all_versions)
                _delete_record_and_draft(record_pid, record_model, draft_model)
        else:
            _delete_record_and_draft(record_pid, record_model, draft_model)

    db.session.commit()

    # Delete record from index
    current_rdm_records_service.indexer.delete(rdm_record)
    if rdm_draft:
        current_rdm_records_service.draft_indexer.delete(rdm_draft)

    for req in requests:
        current_requests_service.indexer.delete(req)


def _flatten(value):
    """Recursively flatten arbitrarily nested lists into scalar leaf values."""
    if isinstance(value, list):
        for item in value:
            yield from _flatten(item)
    else:
        yield value


def _get_field_values(record, field_path):
    """Walk a dotted field path (e.g. metadata.creators) against a record
    dict, walking through lists, and return the flattened leaf values.
    """
    values = [record]
    for part in field_path.split("."):
        next_values = []
        for value in values:
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and part in item:
                        next_values.append(item[part])
            elif isinstance(value, dict) and part in value:
                next_values.append(value[part])
        values = next_values
        if not values:
            return []

    leaves = []
    for value in values:
        leaves.extend(_flatten(value))
    return leaves

PERSON_FIELDS = [
    ("metadata.creators", "creator"),
    ("metadata.contributors", "contributor"),
]


def _person_details(entry):
    """Split a creator/contributor dict into (name, affiliation, orcid)."""
    person_or_org = entry.get("person_or_org", {})
    name = person_or_org.get("name", "")
    orcid = next(
        (
            identifier.get("identifier", "")
            for identifier in person_or_org.get("identifiers", []) or []
            if identifier.get("scheme") == "orcid"
        ),
        "",
    )
    affiliation = "; ".join(
        aff.get("name", "") for aff in entry.get("affiliations", []) or []
    )
    return name, affiliation, orcid


DEFAULT_EXPORT_FIELDS = [
    "id",
    "links.self_html",
    "metadata.title",
]


@cds_admin.command(
    name="export",
    help="A command to export records into a CSV (by default). Temporary solution until we have export functionality.",
)
@click.option(
    "-q",
    "--query",
    type=str,
    required=True,
    help="Search query.",
)
@click.option(
    "-c",
    "--community",
    type=str,
    required=False,
    help="Community slug to scope the query to.",
)
@click.option(
    "-o",
    "--output",
    type=str,
    default="/tmp/records_export.csv",
    show_default=True,
    help="Path of the CSV file to write.",
)
@click.option(
    "--fields",
    type=str,
    multiple=True,
    help=(
        "Dotted path of a scalar field to export as a CSV column, e.g. "
        "metadata.title. Repeatable. Defaults to: "
        + ", ".join(DEFAULT_EXPORT_FIELDS)
        + ". Creators/contributors are not requested here -- see "
        "--include-creatibutors."
    ),
)
@click.option(
    "--include-creatibutors",
    default=True,
    help=(
        "Also export creators/contributors, one row per person split into "
        "role/name/affiliation/orcid columns (repeating the scalar --fields "
        "on each of their rows). When disabled, only the scalar --fields "
        "are exported and each record is a single row."
    ),
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Only print the number of records matching the query, without exporting.",
)
@with_appcontext
def export_records(query, community, output, fields, include_creatibutors, dry_run):
    """Custom script to export records based on query and optionally community slug.

    Usage: invenio cds-admin export -q <query> -c <slug> --fields metadata.title -o out.csv
    """
    search_query = query
    if community:
        community_id = current_communities.service.record_cls.pid.resolve(community).id
        search_query = f"parent.communities.ids:{community_id} AND ({query})"

    if dry_run:
        result = current_rdm_records_service.search(
            system_identity, params={"q": search_query, "size": 1}
        )
        total = result.to_dict()["hits"]["total"]
        click.secho(f"{total} record(s) found matching the query.", fg="green")
        return

    export_fields = list(fields) or DEFAULT_EXPORT_FIELDS

    header = list(export_fields)
    if include_creatibutors:
        header += ["role", "name", "affiliation", "orcid"]

    result = current_rdm_records_service.scan(
        system_identity, params={"q": search_query, "allversions": True}
    )

    count = 0
    with open(output, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for record in result.hits:
            scalar_values = [
                "; ".join(str(v) for v in _get_field_values(record, field))
                for field in export_fields
            ]

            if not include_creatibutors:
                writer.writerow(scalar_values)
                count += 1
                continue

            for field, role in PERSON_FIELDS:
                for entry in _get_field_values(record, field):
                    name, affiliation, orcid = _person_details(entry)
                    writer.writerow(scalar_values + [role, name, affiliation, orcid])
                    count += 1

    click.secho(f"Exported {count} row(s) to {output}.", fg="green")
