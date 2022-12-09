from datetime import datetime

from invenio_rdm_migrator.streams.users import UserTransform, UserEntry


class CDSUserTransform(UserTransform):

    def _user(self, entry):
        """Transform the user."""
        return CDSUserEntry().transform(entry)

    def _session_activity(self, entry):
        """Transform the session activity."""
        return entry.get("session_activity")

    def _tokens(self, entry):
        """Transform the tokens."""
        return entry.get("tokens")

    def _applications(self, entry):
        """Transform the applications."""
        # TODO
        pass

    def _oauth(self, entry):
        """Transform the OAuth accounts."""
        # TODO
        pass

    def _identities(self, entry):
        """Transform the identities."""
        data = entry.get("identities")
        return [
            {
                "id": i["id"],
                "created": i["created"],
                "updated": i["updated"],
                "method": i["method"],
            }
            for i in data or []
        ]


class CDSUserEntry(UserEntry):
    """Transform a single user entry."""

    def _id(self, entry):
        """Returns the user ID."""
        return entry["id"]  #  TODO do we need the old ids?

    def _version_id(self, entry):
        """Returns the version id."""
        return entry.get("version_id", 1)

    def _created(self, entry):
        """Returns the creation date."""
        return entry.get("created", datetime.utcnow().isoformat())

    def _updated(self, entry):
        """Returns the update date."""
        return entry.get("updated", datetime.utcnow().isoformat())

    def _email(self, entry):
        """Returns the email."""
        return entry["email"]

    def _active(self, entry):
        """Returns if the user is active."""
        return False if entry["note"] == "0" else True

    def _confirmed_at(self, entry):
        """Returns the confirmation date."""
        return entry.get("confirmed_at", datetime.utcnow().isoformat())  # TODO do we migrate inactive users ? the ones not present in ldap ?

    def _username(self, entry):
        """Returns the username."""
        return entry.get("email")  # TODO change to LDAP username ?

    def _displayname(self, entry):
        """Returns the displayname."""
        return entry.get("name")

    def _profile(self, entry):
        """Returns the profile."""
        return {
            "full_name": entry.get("name"),
            # "department": entry.get("department")
            # TODO could be displayed as an affiliation ?
        }

    def _password(self, entry):
        return None

    def _preferences(self, entry):
        """Returns the preferences."""
        return {
            "visibility": "restricted",
            "email_visibility": "restricted",
        }

    def _login_information(self, entry):
        """Returns the login information."""
        return {
            "last_login_at": entry.get("last_login"),
            "current_login_at": None,
            "last_login_ip": None,
            "current_login_ip": None,
            "login_count": None,
        }

    def transform(self, entry):
        """Transform a user single entry."""
        return {
            "id": self._id(entry),
            "created": self._created(entry),
            "updated": self._updated(entry),
            "version_id": self._version_id(entry),
            "email": self._email(entry),
            "active": self._active(entry),
            "password": self._password(entry),
            "confirmed_at": self._confirmed_at(entry),
            "username": self._username(entry),
            "displayname": self._displayname(entry),
            "profile": self._profile(entry),
            "preferences": self._preferences(entry),
            "login_information": self._login_information(entry),
        }
