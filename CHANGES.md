# Changes

Version 1.0.17 (released 2024-10-09)

- remove departments, experiments and CERN subjects

Version 1.0.16 (released 2024-10-07)

- global: upgrade codebase
- global: add redirection from legacy recids
- templates: fix js block inheritance
- config: add MathJax support

Version 1.0.15 (released 2024-08-28)

- global: upgrade codebase to invenio-app-rdm 13.0.0b1.dev2
- templates: add email templates
- vocabularies: add funders
- files: add offloading files to EOS
- permissions: add oais-archiver role
- permissions: add archiver role
- vocabularies: add subjects, experiments, departments
- pages: fix static pages

Version 1.0.14 (released 2024-05-27)

- installation: upper pin flask-mail
- installation: upgrade invenio-app-rdm (fixes DOI restriction tombstone)

Version 1.0.13 (released 2024-05-22)

- global: upgrade package-lock.json

Version 1.0.12 (released 2024-05-22)

- global: upgrade codebase to invenio-app-rdm v12.0.0b3.dev17

Version 1.0.11 (released 2024-04-04)

- templates: fix duplicate subject block

Version 1.0.10 (released 2024-04-04)

- templates: add template for community submission accept action
- templates: update existing notification templates
- global: upgrade codebase to invenio-app-rdm v12.0.0b3.dev8

Version 1.0.9 (released 2024-04-02)

- global: upgrade codebase to invenio-app-rdm v12.0.0b3.dev7

Version 1.0.8 (released 2024-02-09)

* add support for file offloading

Version 1.0.7 (released 2023-09-14)

* make person_id optional arg on login for external accounts

Version 1.0.6 (released 2023-09-12)

* temporary fix in the record details template

Version 1.0.5 (released 2023-08-28)

* bump invenio-oauthclient to integrate the changes in group fetching

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
