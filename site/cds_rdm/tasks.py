# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2023 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Celery tasks for cds."""

from celery import shared_task
from invenio_cern_sync.groups.sync import sync as groups_sync
from invenio_cern_sync.users.sync import sync as users_sync
from invenio_users_resources.services.users.tasks import reindex_users
from flask import current_app
from invenio_access.permissions import system_identity
from invenio_accounts.models import User
from invenio_records_resources.proxies import current_service_registry
from invenio_records_resources.services.uow import UnitOfWork
from invenio_search.engine import dsl
from marshmallow import ValidationError
from sqlalchemy.orm.exc import NoResultFound

@shared_task
def sync_users(since=None, **kwargs):
    """Task to sync users with CERN database."""
    user_ids = users_sync(identities=dict(since=since))
    reindex_users.delay(user_ids)


@shared_task
def sync_groups(since=None, **kwargs):
    """Task to sync groups with CERN database."""
    groups_sync(groups=dict(since=since))


@shared_task()
def sync_local_accounts_to_names(since=None, user_id=None):
    """
    Syncs local accounts to the names vocabulary based on user profile data.

    This function updates or creates name entries in the vocabulary, syncing information
    such as given name, family name, email, affiliations, ORCID identifiers, and additional
    properties (e.g., group, department, section).

    If the name is marked as "unlisted" (indicating that it is deprecated), and/or there
    is already an ORCID value present, it will resolve the orcid value and sync the
    information into that value as well. When syncing it to the ORCID value, it will only
    add the affiliations, identifiers, tags, and properties that are not already present.

    For ORCID values, given name and family name are not synced. If they change at CERN,
    the ORCID value should be updated and synced through the ORCID harvester.

    param since: The date (iso format) from which to sync the users.
    param user_id: The user id to sync.
    """

    def _add_affiliations(user, name, updated_name, updated=False):
        """Updates the affiliations of the name.

        param user: The user object.
        param name: The name dictionary.
        param updated_name: The updated name dictionary.
        param updated: If the name has already been updated.
        """
        user_affiliation = user.user_profile.get("affiliations", "")
        name_affiliations = [aff["name"] for aff in name.get("affiliations", [])]
        if user_affiliation and user_affiliation not in name_affiliations:
            if "affiliations" not in updated_name:
                updated_name["affiliations"] = []
            updated_name["affiliations"].append({"name": user_affiliation})
            updated = True
        return updated

    def _add_orcid(user, name, updated_name, updated=False):
        """Adds the ORCID value to the name.

        param user: The user object.
        param name: The name dictionary.
        param updated_name: The updated name dictionary.
        param updated: If the name has already been updated.
        """
        user_orcid = user.user_profile.get("orcid")
        name_orcids = [
            identifier["identifier"]
            for identifier in name.get("identifiers", [])
            if identifier["scheme"] == "orcid"
        ]
        if user_orcid and user_orcid not in name_orcids:
            if "identifiers" not in updated_name:
                updated_name["identifiers"] = []
            updated_name["identifiers"].append(
                {"scheme": "orcid", "identifier": user_orcid}
            )
            updated = True
        return updated

    def _add_or_update_props(user, name, updated_name, updated=False):
        """Adds or updates the props of the name.

        param user: The user object.
        param name: The name dictionary.
        param updated_name: The updated name dictionary.
        param updated: If the name has already been updated.
        """
        for prop in prop_values:
            user_prop = user.user_profile.get(prop)
            name_prop = name.get("props", {}).get(prop)
            if user_prop and user_prop != name_prop:
                if "props" not in updated_name:
                    updated_name["props"] = {}
                updated_name["props"][prop] = user_prop
                updated = True

        default_props = _get_default_props(user.id)
        for key, value in default_props.items():
            if key not in name.get("props", {}):
                if "props" not in updated_name:
                    updated_name["props"] = {}
                updated_name["props"][key] = value
                updated = True

        return updated

    def _add_or_update_email(user, name, updated_name, updated=False):
        """Adds or updates the email of the name.

        param user: The user object.
        param name: The name dictionary.
        param updated_name: The updated name dictionary.
        param updated: If the name has already been updated.
        """
        if user.email and user.email != name.get("props", {}).get("email"):
            if "props" not in updated_name:
                updated_name["props"] = {}
            updated_name["props"]["email"] = user.email
            updated = True
        return updated

    def _check_if_update_needed(
        user, name, cds_id=None, is_orcid=False, deprecate=False
    ):
        """Check if the name needs to be updated.

        param user: The user object.
        param name: The name dictionary.
        param cds_id: The CDS identifier.
        param is_orcid: If the name passed is an ORCID value.
        param deprecate: If the name should be marked as unlisted.
        """

        updated = False
        updated_name = {**name}

        cds_identifier = next(
            (
                identifier.get("identifier")
                for identifier in name.get("identifiers", [])
                if identifier.get("scheme") == "cds"
            ),
            None,
        )

        # If the CDS identifier is not present, we add it
        if cds_id and not cds_identifier:
            if updated_name.get("identifiers"):
                updated_name["identifiers"].append(
                    {"scheme": "cds", "identifier": cds_id}
                )
            else:
                updated_name["identifiers"] = [{"scheme": "cds", "identifier": cds_id}]
            updated = True

        # We only update the names if it's a non ORCID value, for ORCID values
        # we rely on the ORCID harvester to update the given name, family name
        if not is_orcid:
            if user.user_profile.get("given_name") != name.get("given_name"):
                updated_name["given_name"] = user.user_profile.get("given_name")
                updated = True

            if user.user_profile.get("family_name") != name.get("family_name"):
                updated_name["family_name"] = user.user_profile.get("family_name")
                updated = True

        update_functions = [
            _add_affiliations,
            _add_orcid,
            _add_or_update_props,
            _add_or_update_email,
        ]

        for update_func in update_functions:
            updated = update_func(user, name, updated_name, updated=updated) or updated

        if deprecate and "unlisted" not in updated_name.get("tags", []):
            if updated_name.get("tags"):
                updated_name["tags"].append("unlisted")
            else:
                updated_name["tags"] = ["unlisted"]
            updated = True

        return updated_name if updated else None

    def _update_name(
        user, name_dict, cds_id=None, is_orcid=False, deprecate=False, uow=None
    ):
        """Updates the name with the new values.

        param user: The user object.
        param name_dict: The name dictionary.
        param is_orcid: If the name passed is an ORCID value.
        """
        updated_name = _check_if_update_needed(
            user, name_dict, cds_id, is_orcid, deprecate
        )
        if updated_name:
            try:
                names_service.update(
                    system_identity, name_dict.get("id"), updated_name, uow=uow
                )
            except ValidationError as e:
                current_app.logger.error(f"Error updating name for user {user.id}: {e}")

    def _update_author(author, user, uow=None):
        """Updates the author record with the new values."""
        updated = False
        if author["given_name"] != user.user_profile.get("given_name"):
            author["given_name"] = user.user_profile.get("given_name")
            updated = True

        if author["family_name"] != user.user_profile.get("family_name"):
            author["family_name"] = user.user_profile.get("family_name")
            updated = True
        
        if author["affiliations"] != user.user_profile.get("affiliations"):
            author["affiliations"] = user.user_profile.get("affiliations")
            updated = True
        
        if updated:
            current_authors_service.update(system_identity, author["id"], author, uow=uow)

        return author

    def _create_author(user, uow=None):
        """Creates the author record."""
        author = {
            "given_name": user.user_profile.get("given_name"),
            "family_name": user.user_profile.get("family_name"),
            "affiliations": user.user_profile.get("affiliations", []),
            "user_id": str(user.id),
        }
        return current_authors_service.create(system_identity, author, uow=uow)

    def _update_or_create_author(user, uow=None):
        """Updates or creates the author record."""
        user_id = user.id
        try:
            author = current_authors_service.get_by_user_id(system_identity, user_id)
            return _update_author(author, user, uow=uow)
        except NoResultFound:
            return _create_author(user, uow=uow)

    def _create_new_name(user, _id, deprecate=False, uow=None):
        """Creates a new name for the user.

        param user: The user object.
        """

        default_props = _get_default_props(user.id)
        name = {
            "id": _id,
            "props": default_props,
            "identifiers": [{"scheme": "cds", "identifier": _id}],
        }

        if user.user_profile.get("given_name"):
            name["given_name"] = user.user_profile.get("given_name")
        if user.user_profile.get("family_name"):
            name["family_name"] = user.user_profile.get("family_name")
        if user.user_profile.get("affiliations"):
            name["affiliations"] = [{"name": user.user_profile.get("affiliations", "")}]
        if user.user_profile.get("orcid"):
            name["identifiers"].append(
                {"scheme": "orcid", "identifier": user.user_profile.get("orcid")}
            )
        for prop in prop_values:
            if user.user_profile.get(prop):
                name["props"][prop] = user.user_profile.get(prop)
        if user.email:
            name["props"]["email"] = user.email
        if deprecate:
            name["tags"] = ["unlisted"]
        try:
            names_service.create(system_identity, name, uow=uow)
        except ValidationError as e:
            current_app.logger.error(f"Error creating name for user {user.id}: {e}")

    def _fetch_name_by_id(id):
        """Fetches the name by the id.

        param id: The id.
        """
        return names_service.read(system_identity, str(id)).to_dict()

    def _fetch_name_by_user_id(user_id):
        """Fetches the name by the user id.

        param user_id: The user id.
        """
        filter = dsl.Q(
            "bool",
            must=[
                dsl.Q("term", **{"props.user_id": str(user_id)}),
                dsl.Q("prefix", id="cds:a:"),
            ],
        )
        names = names_service.search(system_identity, extra_filter=filter)
        if names.total == 0:
            return None
        elif names.total > 1:
            raise ValueError("More than one name found for the same user.")

        return next(names.hits)

    def _get_default_props(user_id):
        """Get the default props for the name."""
        return {"is_cern": True, "user_id": str(user_id)}

    if not since and not user_id:
        raise ValueError("since or user_id must be provided)")

    prop_values = ["group", "department", "section"]
    names_service = current_service_registry.get("names")
    users = []

    # Allows to sync a single user
    if user_id:
        try:
            users = [User.query.filter(User.id == user_id).one()]
        except Exception as e:
            current_app.logger.warning(f"User with id {user_id} not found.")
            raise e
    else:
        users = User.query.filter(User.updated > since).all()
    existing_name_dict = None
    for user in users:
        cds_name_dict = _fetch_name_by_user_id(user.id)
        orcid = user.user_profile.get("orcid")
        try:
            # 1. We update the ORCID value if there is any and mark
            # the original for deprecation
            existing_name_dict = _fetch_name_by_id(orcid)
            with UnitOfWork(db.session) as uow:
                author = _update_or_create_author(user, uow=uow)

                # Mark the original cds entry as deprecated if not already unlisted
                if cds_name_dict:
                    _update_name(user, cds_name_dict, deprecate=True, uow=uow)

                # Update the ORCID value
                _update_name(
                    user,
                    existing_name_dict,
                    cds_id=author.pid.pid_value,
                    is_orcid=True,
                    uow=uow,
                )
                uow.commit()
        except NoResultFound:
            current_app.logger.info(f"No ORCID value found for user {user.id}.")
            if cds_name_dict:
                # 2. We update the author and name value if it exists
                with UnitOfWork(db.session) as uow:
                    _update_name(user, cds_name_dict, uow=uow)
                    _update_or_create_author(user, uow=uow)
                    uow.commit()
            else:
                # 3. If the name doesn't exist, we create a new one
                try:
                    with UnitOfWork(db.session) as uow:
                        author = _update_or_create_author(
                            user, uow=uow
                        )  # Creates the author record
                        _create_new_name(
                            user,
                            author.pid.pid_value,
                            uow=uow,
                        )  # Creates the name record using the author PID
                        uow.commit()
                except Exception as e:
                    current_app.logger.error(
                        f"Error creating name for user {user.id}: {e}"
                    )


@shared_task()
def merge_duplicate_names_vocabulary(since=None):
    """
    Merges duplicate names in the names vocabulary based on ORCID identifiers.

    This task identifies and merges duplicate entries in the names vocabulary when users
    have overlapping records between the CERN database and ORCID. The merging process consolidates
    all relevant data (such as affiliations, identifiers, tags, and properties) into a single
    ORCID-based record. The source records are marked as "unlisted" to indicate deprecation,
    preventing them from being displayed in search results while preserving historical integrity.

    Existing records authored by these users are not affected by the deprecation status,
    but search displays will exclude deprecated records.
    """

    def _name_is_orcid_value(name, orcid_value):
        """Check if the name is an ORCID value."""
        return name["id"] == orcid_value

    def _merge(name_source, name_dest):
        """Merges the names.

        param name_source: The name to merge from. This will marked as unlisted after the merge, meaning that won't be returned in the search results.
        param name_dest: The name to merge to.
        """
        updated = False
        # Merge the affiliations
        affiliations_dest = name_dest.get("affiliations", [])
        for affiliation_source in name_source.get("affiliations", []):
            if affiliation_source not in affiliations_dest:
                affiliations_dest.append(affiliation_source)
                updated = True

        name_dest["affiliations"] = affiliations_dest

        # Merge the identifiers
        identifiers_dest = name_dest.get("identifiers", [])
        for identifier_source in name_source.get("identifiers", []):
            if identifier_source not in identifiers_dest:
                identifiers_dest.append(identifier_source)
                updated = True
        name_dest["identifiers"] = identifiers_dest

        # Merge the tags (except "unlisted" value)
        tags_dest = name_dest.get("tags", [])
        tags_source = name_source.get("tags", [])
        for tag_source in tags_source:
            if tag_source not in tags_dest and tag_source != "unlisted":
                tags_dest.append(tag_source)
                updated = True
        name_dest["tags"] = tags_dest

        # Merge the props
        props_dest = name_dest.get("props", {})
        for key, value in name_source.get("props", {}).items():
            if key not in props_dest:
                props_dest[key] = value
                updated = True
        name_dest["props"] = props_dest

        # Mark as unlisted the name_source value
        if "unlisted" not in tags_source:
            if tags_source:
                name_source["tags"] = tags_source + ["unlisted"]
            else:
                name_source["tags"] = ["unlisted"]
            current_app.logger.info(
                f"Marking name {name_source.get('id')} as unlisted after merging."
            )
            # "Deprecate" the name_source value
            names_service.update(system_identity, name_source.get("id"), name_source)

        if updated:
            current_app.logger.info(
                f"Merging name {name_source.get('id')} into name {name_dest.get('id')}."
            )
            # Update the name_dest value
            names_service.update(system_identity, name_dest.get("id"), name_dest)

    def _get_orcid_value(name):
        """Get the ORCID value from the name."""
        return next(
            (
                identifier.get("identifier")
                for identifier in name.get("identifiers", [])
                if identifier.get("scheme") == "orcid"
            ),
            None,
        )

    names_service = current_service_registry.get("names")

    filters = [
        dsl.Q("term", **{"props.is_cern": True}),
        dsl.Q("term", **{"identifiers.scheme": "orcid"}),
        dsl.Q("bool", must_not=[dsl.Q("term", tags="unlisted")]),
    ]
    if since:
        filters.append(dsl.Q("range", updated={"gte": since}))
    combined_filter = dsl.Q("bool", filter=filters)

    names = names_service.scan(system_identity, extra_filter=combined_filter)

    for name in names.hits:
        orcid_value = _get_orcid_value(name)
        if orcid_value:
            names_to_merge = names_service.resolve(
                system_identity, id_=orcid_value, id_type="orcid", many=True
            )
            if names_to_merge.total > 1:
                # We get the ORCID value and merge all the other values into it
                # (Ideally there should be only 1 value apart from the ORCID)
                orcid_name = None
                other_names = []
                for name_dest_merge in names_to_merge.hits:
                    if _name_is_orcid_value(name_dest_merge, orcid_value):
                        orcid_name = name_dest_merge
                    else:
                        other_names.append(name_dest_merge)

                if orcid_name:
                    for name_dest_merge in other_names:
                        _merge(name_dest_merge, orcid_name)
