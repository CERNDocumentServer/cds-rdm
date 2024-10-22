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
def sync_local_accounts_to_names(since, user_id=None):
    """Syncs local accounts to names vocabulary.

    If the name is marked as "unlisted" - meaning it is deprecated - we still update it with the new values, if needed.
    """
    prop_values = ["group", "department", "maibox", "section"]
    service = current_service_registry.get("names")

    def _check_if_update_needed(user, name, is_orcid=False):
        """Check if the name needs to be updated."""

        updated = False
        updated_name = {**name}

        if not is_orcid:
            if user.user_profile.get("given_name") != name.get("given_name"):
                updated_name["given_name"] = user.user_profile.get("given_name")
                updated = True

            if user.user_profile.get("family_name") != name.get("family_name"):
                updated_name["family_name"] = user.user_profile.get("family_name")
                updated = True

        user_affiliation = user.user_profile.get("affiliations", "")
        name_affiliations = [aff["name"] for aff in name.get("affiliations", [])]
        if user_affiliation and user_affiliation not in name_affiliations:
            if "affiliations" not in updated_name:
                updated_name["affiliations"] = []
            updated_name["affiliations"].append({"name": user_affiliation})
            updated = True

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

        for prop in prop_values:
            user_prop = user.user_profile.get(prop)
            name_prop = name.get("props", {}).get(prop)
            if user_prop and user_prop != name_prop:
                if "props" not in updated_name:
                    updated_name["props"] = {}
                updated_name["props"][prop] = user_prop
                updated = True

        # add the email as props
        if user.email and user.email != name.get("props", {}).get("email"):
            if "props" not in updated_name:
                updated_name["props"] = {}
            updated_name["props"]["email"] = user.email
            updated = True

        return updated_name if updated else None

    def _update_name(user, name_dict, is_orcid=False):
        """Updates the name with the new values."""
        updated_name = _check_if_update_needed(user, name_dict, is_orcid)
        if updated_name:
            try:
                service.update(system_identity, name_dict.get("id"), updated_name)
            except ValidationError as e:
                current_app.logger.error(f"Error updating name for user {user.id}: {e}")

    def _create_new_name(user):
        name = {"id": str(user.id), "props": {"is_cern": True}}

        if user.user_profile.get("given_name"):
            name["given_name"] = user.user_profile.get("given_name")
        if user.user_profile.get("family_name"):
            name["family_name"] = user.user_profile.get("family_name")
        if user.user_profile.get("affiliations"):
            name["affiliations"] = [{"name": user.user_profile.get("affiliations", "")}]
        if user.user_profile.get("orcid"):
            name["identifiers"] = [
                {"scheme": "orcid", "identifier": user.user_profile.get("orcid")}
            ]
        for prop in prop_values:
            if user.user_profile.get(prop):
                name["props"][prop] = user.user_profile.get(prop)
        try:
            service.create(system_identity, name)
        except ValidationError as e:
            current_app.logger.error(f"Error creating name for user {user.id}: {e}")

    users = []
    # Allows to sync a single user
    if user_id:
        user = User.query.get(user_id)
        users = [user] if user else []
    else:
        users = User.query.filter(User.updated > since).all()
    name_dict = None
    for user in users:
        orcid = None
        try:
            name_dict = service.read(system_identity, str(user.id)).to_dict()
            _update_name(user, name_dict)
        except NoResultFound:
            orcid = user.user_profile.get("orcid")
            if orcid:
                try:
                    # Check if the ORCID value is already present and update it
                    name_dict = service.read(system_identity, orcid).to_dict()
                    _update_name(user, name_dict, is_orcid=True)
                except NoResultFound:
                    _create_new_name(user)
            else:
                _create_new_name(user)



@shared_task()
def merge_duplicate_names_vocabulary(since=None):
    """Merges duplicate names in the names vocabulary."""
    service = current_service_registry.get("names")

    def _merge(name_from, name_to):
        """Merges the names.

        param name_from: The name to merge from. This will marked as unlisted after the merge, meaning that won't be returned in the search results.
        param name_to: The name to merge to.
        """
        updated = False
        # Merge the affiliations
        affiliations_to = name_to.get("affiliations", [])
        for affiliation_from in name_from.get("affiliations", []):
            if affiliation_from not in affiliations_to:
                affiliations_to.append(affiliation_from)
                updated = True

        name_to["affiliations"] = affiliations_to

        # Merge the identifiers
        identifiers_to = name_to.get("identifiers", [])
        for identifier_from in name_from.get("identifiers", []):
            if identifier_from not in identifiers_to:
                identifiers_to.append(identifier_from)
                updated = True
        name_to["identifiers"] = identifiers_to

        # Merge the tags (except "unlisted" value)
        tags_to = name_to.get("tags", [])
        tags_from = name_from.get("tags", [])
        for tag_from in tags_from:
            if tag_from not in tags_to and tag_from != "unlisted":
                tags_to.append(tag_from)
                updated = True
        name_to["tags"] = tags_to

        # Merge the props
        props_to = name_to.get("props", {})
        for key, value in name_from.get("props", {}).items():
            if key not in props_to:
                props_to[key] = value
                updated = True
        name_to["props"] = props_to

        # Mark as unlisted the name_from value
        if "unlisted" not in tags_from:
            if tags_from:
                name_from["tags"] = tags_from + ["unlisted"]
            else:
                name_from["tags"] = ["unlisted"]

            # "Deprecate" the name_from value
            service.update(system_identity, name_from.get("id"), name_from)

        if updated:
            # Update the name_to value
            service.update(system_identity, name_to.get("id"), name_to)

    filters = [
        dsl.Q("term", **{"props.is_cern": True}),
        dsl.Q("term", **{"identifiers.scheme": "orcid"}),
        dsl.Q("bool", must_not=[dsl.Q("term", tags="unlisted")]),
    ]
    if since:
        filters.append(dsl.Q("range", updated={"gte": since}))
    combined_filter = dsl.Q("bool", filter=filters)

    names = service.scan(system_identity, extra_filter=combined_filter)

    for name in names.hits:
        orcid = next(
            (
                identifier.get("identifier")
                for identifier in name.get("identifiers", [])
                if identifier.get("scheme") == "orcid"
            ),
            None,
        )
        if orcid:
            names_to_merge = service.resolve(
                system_identity, id_=orcid, id_type="orcid", many=True
            )
            if names_to_merge.total > 1:
                # We get the ORCID value and merge all the other values into it (Ideally there should be only 1 value apart from the ORCID)
                orcid_name = None
                other_names = []
                for name_to_merge in names_to_merge.hits:
                    if name_to_merge["id"] == orcid:
                        orcid_name = name_to_merge
                    else:
                        other_names.append(name_to_merge)

                if orcid_name:
                    for name_to_merge in other_names:
                        _merge(name_to_merge, orcid_name)
