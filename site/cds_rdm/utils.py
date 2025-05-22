# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2024 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Utilities for cds."""

import idutils
from flask import current_app
from invenio_access.permissions import system_identity
from invenio_records_resources.services.errors import ValidationError


class NamesUtils:
    """Names utilities."""

    def __init__(self, prop_values=None, service=None):
        """Constructor."""
        self.prop_values = prop_values
        self.service = service

    def add_affiliations(self, user, name, updated_name, updated=False):
        """Updates the affiliations of the name.

        :param user: The user object.
        :param name: The name dictionary.
        :param updated_name: The updated name dictionary.
        :param updated: If the name has already been updated.
        :return: Boolean indicating if the name was updated.
        """
        user_affiliation = user.user_profile.get("affiliations", "")
        name_affiliations = [aff["name"] for aff in name.get("affiliations", [])]
        if user_affiliation and user_affiliation not in name_affiliations:
            if "affiliations" not in updated_name:
                updated_name["affiliations"] = []
            updated_name["affiliations"].append({"name": user_affiliation})
            updated = True
        return updated

    def add_orcid(self, user, name, updated_name, updated=False):
        """Adds the ORCID value to the name.

        :param user: The user object.
        :param name: The name dictionary.
        :param updated_name: The updated name dictionary.
        :param updated: If the name has already been updated.
        :return: Boolean indicating if the name was updated.
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

    def add_or_update_props(self, user, name, updated_name, updated=False):
        """Adds or updates the props of the name.

        :param user: The user object.
        :param name: The name dictionary.
        :param updated_name: The updated name dictionary.
        :param updated: If the name has already been updated.
        :return: Boolean indicating if the name was updated.
        """
        for prop in self.prop_values:
            user_prop = user.user_profile.get(prop)
            name_prop = name.get("props", {}).get(prop)
            if user_prop and user_prop != name_prop:
                if "props" not in updated_name:
                    updated_name["props"] = {}
                updated_name["props"][prop] = user_prop
                updated = True

        default_props = self.get_default_props(user.id)
        for key, value in default_props.items():
            if key not in name.get("props", {}):
                if "props" not in updated_name:
                    updated_name["props"] = {}
                updated_name["props"][key] = value
                updated = True

        return updated

    def add_or_update_email(self, user, name, updated_name, updated=False):
        """Adds or updates the email of the name.

        :param user: The user object.
        :param name: The name dictionary.
        :param updated_name: The updated name dictionary.
        :param updated: If the name has already been updated.
        :return: Boolean indicating if the name was updated.
        """
        if user.email and user.email != name.get("props", {}).get("email"):
            if "props" not in updated_name:
                updated_name["props"] = {}
            updated_name["props"]["email"] = user.email
            updated = True
        return updated

    def check_if_update_needed(self, user, name, unlist=False):
        """Check if the name needs to be updated.

        :param user: The user object.
        :param name: The name dictionary.
        :param unlist: If the name should be marked as unlisted.
        :return: Updated name dictionary if updated, else None.
        """
        updated = False
        updated_name = {**name}

        # We only update the names if it's a non ORCID value, for ORCID values
        # we rely on the ORCID harvester to update the given name, family name
        if idutils.is_orcid(name["id"]):
            if user.user_profile.get("given_name") != name.get("given_name"):
                updated_name["given_name"] = user.user_profile.get("given_name")
                updated = True

            if user.user_profile.get("family_name") != name.get("family_name"):
                updated_name["family_name"] = user.user_profile.get("family_name")
                updated = True

        update_functions = [
            self.add_affiliations,
            self.add_orcid,
            self.add_or_update_props,
            self.add_or_update_email,
        ]

        for update_func in update_functions:
            updated = update_func(user, name, updated_name, updated=updated) or updated

        if unlist and "unlisted" not in updated_name.get("tags", []):
            if updated_name.get("tags"):
                updated_name["tags"].append("unlisted")
            else:
                updated_name["tags"] = ["unlisted"]
            updated = True

        return updated_name if updated else None

    def update_name(self, user, name_dict, unlist=False, uow=None):
        """Updates the name with the new values.

        :param user: The user object.
        :param name_dict: The name dictionary.
        :param unlist: If the name should be marked as unlisted.
        :param uow: Unit of work.
        """
        updated_name = self.check_if_update_needed(user, name_dict, unlist)
        if updated_name:
            try:
                self.service.update(
                    system_identity, name_dict["id"], updated_name, uow=uow
                )
            except ValidationError as e:
                current_app.logger.error(f"Error updating name for user {user.id}: {e}")

    def create_new_name(self, user, unlist=False, uow=None):
        """Creates a new name for the user.

        :param user: The user object.
        :param uow: Unit of work.
        """
        default_props = self.get_default_props(user.id)
        name = {
            "id": str(user.user_profile["person_id"]),
            "props": default_props,
            "identifiers": [],
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

        for prop in self.prop_values:
            if user.user_profile.get(prop):
                name["props"][prop] = user.user_profile.get(prop)

        if user.email:
            name["props"]["email"] = user.email

        if unlist:
            name["tags"] = ["unlisted"]

        try:
            self.service.create(system_identity, name, uow=uow)
        except ValidationError as e:
            current_app.logger.error(f"Error creating name for user {user.id}: {e}")

    def fetch_name_by_id(self, id):
        """Fetches the name by the id.

        :param id: The id.
        :return: Name dictionary.
        """
        return self.service.read(system_identity, str(id)).to_dict()

    @staticmethod
    def get_default_props(user_id):
        """Get the default props for the name.

        :param user_id: The user id.
        :return: Dictionary of default properties.
        """
        return {"is_cern": True, "user_id": str(user_id)}

    def merge(self, name_source, name_dest):
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
            self.service.update(system_identity, name_source.get("id"), name_source)

        if updated:
            current_app.logger.info(
                f"Merging name {name_source.get('id')} into name {name_dest.get('id')}."
            )
            # Update the name_dest value
            self.service.update(system_identity, name_dest.get("id"), name_dest)


def evaluate_permissions(record, actions):
    """Evaluates permissions for a record."""
    return record.has_permissions_to(actions)
