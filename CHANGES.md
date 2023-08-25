# Changes

Version 1.0.4 (released 2023-08-25)

* fix new version drafts pointing to edit drafts when cleanup_drafts script was
  running to purge all soft-deleted drafts (invenio-app-rdm/issues/2197)
* update `read_latest` to be able to fetch record by passign the parent id (zenodo/rdm-project#174)
* fetch groups async to improve login performance

Version 1.0.3 (released 2023-08-17)

* Fix temporarily permissions on who can add a record to a community so that
  community curators can submit a record to other communities

Version 1.0.2 (released 2023-07-31)

* Decrease user sync task logging level

Version 1.0.1 (released 2023-07-28)

* Improve e-mail templates
* Add missing username field when syncing users from LDAP

Version 1.0.0 (released 2023-07-25)

* Restrict who can create communities via role/user needs
* Fix display banner
* Make sync users/groups tasks running only on deployed envs
* Add funders/awards
