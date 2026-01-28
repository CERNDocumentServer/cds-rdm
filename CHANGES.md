# Changes

Version 1.25.3 (release 2026-01-28)

- upgrade invenio-rdm-records

Version 1.25.2 (release 2026-01-27)

- fix(versions): typo in component rendering

Version 1.25.1 (release 2026-01-26)

- fix(versions): show copy button only in published versions

Version 1.25.0 (release 2026-01-26)

- fix(unlock-files): prevent automatic unlock of files for admins
- feat(versions): Override version box jinja template
- change(harvester): transformation architecture upgrade
- fix(harvester): thesis custom fields mappings

Version 1.24.1 (release 2026-01-16)

- feat(homepage): add link to docs in the footer

Version 1.24.0 (release 2026-01-16)

- refactor(templates): apply changes to customize file display name 
- fix(templates): Add id to files list div 
- refactor(redirector): Redirect /files to record with ?preview_file 
- assets: overrides: Update lock/unlock helptext 
- uv: upgrade version of app-rdm and react-invenio-forms 
- feat(reply-comments): allow request users to reply when conversation is locked 
- config: request locking enabled 
- feat(previewer): add gltf previewer

Version 1.23.0 (release 2026-01-08)

- vocabularies: departments: Add CIO
- frontpage: Add CIO community

Version 1.22.0 (released 2025-12-19)

- feat(records): override files template to customize file display name
- fix(redirector): Find file in older versions if no version provided
- fix(redirector): Redirect to download for non-previewable files
- fix(legacy): handle PermissionDeniedError in legacy file redirects
- fix(theme): decrease the environment bar
- fix(components): Raise ValidationErrorWithMessageAsList

Version 1.21.0 (released 2025-12-15)

- add(clc sync): link to remove sync
- add(resouce_type): memorandum, form, template
- add(schemes): HAL identifier
- fix(ids): remove duplicated handle scheme
- invenio.cfg: Move bibtex formatters together in dropdown
- add(community): add department community type
- add(grants): add Helix Nebula award
- fix(harvester): related identifiers relation type assignment

Version 1.20.0 (released 2025-11-13)

- installation: upgrade dependencies
- refactor(components): Validate and reserve on publish before register
- fix(resource_types): remove image-photo from deposit
- resource-types: added new types for periodicals and brochure
- refactor(config): Rename CDS Reference->CDS Report Number
- refactor(components): Make cdsrn reusable between record versions
- feat(tasks): Add shared_task on publish to maintain DB consistency for cdsrn

Version 1.19.0 (released 2025-11-06)

- installation: upgrade dependencies
- fix(harvester): find existing records by related ID
- fix(harvester): related identifiers assignment
- feat(permissions): add external DOI file modification
- fix(ui): hide cds id from names
- installation: update package-lock
- feat(os): bump OpenSearch to v3.2.0
- fix(setup): add s3fs missing dependency
- feat(setup): bump invenio-cern-sync
- feat(install): migrate to uv
- fix(permissions): simplify locked files permissions
- fix(harvester): handling languages
- feat(fixtures): add CERN Research community fixture
- fix(harvester): fix record with external DOI file management
- fix(jobs): fix date serialization for harvester
- feat(permissions): add external DOI file modification
- schemes: added scheme for indico links
- inspire_harvester: allow multiple document types

Version 1.18.0 (released 2025-10-30)

- installation: upgrade major dependencies
- config:  Rename lcds -> cds
- config: Disable minting cdsrn identifier
- feat(components): mint cdsrn to ensure uniqueness
- config: rename cds_ref to cdsrn
- style: add favicon and static image for doc
- identifiers: separated alternate and related identifiers
- fix(custom_fields): fix broken links with landing_page_search_attr
- inspire_harvester: rename publication-thesis->publication-dissertation

Version 1.17.0 (released 2025-10-14)

- installation: upgrade invenio-app-rdm (bugfix)

Version 1.16.0 (released 2025-10-13)

- jobs subtasks tracking
- harvester:
  - unblock all document types to harvest
  - fix experiments/accelerators mappings
- add administrative unit custom field
- rename resource type to text, added new resource types for admin docs
- fix user search
- add new accelerator (CESAR)
- add search to resource type field
- add structure for new preview
- add display "Indexed in INSPIRE"

Version 1.15.2 (released 2025-09-01)

- pipfile: bump invenio-app-rdm and invenio-rdm-records (optional DOI fix)

Version 1.15.1 (released 2025-08-12)

- installation: upgrade invenio packages (invenio-jobs fix)

Version 1.15.0 (released 2025-08-06)

- global: add OAISERVER_XSL_URL
- jobs: fix since argument serialization
- deposit: add CDS content policy checkboxes on publish
- landing page: add bibtex export option for all versions
- requests: add reviewers (disabled on prod in this version)

Version 1.14.0 (released 2025-06-25)

- schemes: add url generator in related identifiers CDS scheme
- thesis: add metadata checks for student programme for thesis resource
- INSPIRE harvester: implement transformer rules
- update packages

Version 1.13.0 (released 2025-06-04)

- permissions: add librarian role to manage clc sync
- views: fix variable name

Version 1.12.0 (released 2025-05-26)

- audit-logs: add administration UI changes

Version 1.11.0 (released 2025-05-21)

- deps: update invenio-cern-sync
- clc: add clc sync message
- clc_sync: improve display

Version 1.10.4 (released 2025-05-16)

- deps: updates dependencies to include fix for Mathjax in citations box
- fixtures: remove redundant empty template
- migration: remove search and collection redirectio

Version 1.10.3 (released 2025-05-15)

- deps: upgrade invenio-app-rdm dependency to v13.0.0b3.dev9

Version 1.10.2 (released 2025-05-15)

- clc_sync: improve fetching based on permissions
- clc_sync: fix display

Version 1.10.1 (released 2025-05-15)

- components: fix thesis validation on already publiched record in csc community
- components: fix empty subject field
- search: fix mappings
- config: fix RDM_RECORDS_SERVICE_COMPONENTS
- components: fix publish without save
- tests: add subject validation component tests
- components: add component for system subject validation
- search: add more mappings for custom fields
- components: add CDSResourcePublication to enforce scientific records to be part of CERN Scientific Community

Version 1.10.0 (released 2025-05-12)

- installation: update dependencies
- CI: upgrade tests OS
- redirector: integrate invenio_url_for
- search: add mappings for custom fields
- dockerpublish: fix tagging rules
- harvester: add logging
- custom fields: add meeting field
- global: add CLC sync module

Version 1.9.0 (released 2025-04-10)

- pipfile: upgrade deps
- doi: add custom validation
- dashboard: add shared with me requests and uploads

Version 1.8.0 (released 2025-03-11)

- Upgrade dependencies for Flask v3

Version 1.7.1 (released 2025-01-27)

- package-lock: update react-invenio-forms

Version 1.7.0 (released 2025-01-27)

- pipfile: upgrade dependencies

Version 1.6.3 (released 2025-01-24)

- assets: lift banner in upper layer

Version 1.6.2 (released 2025-01-23)

- views: override view via config
- assets: fix banner links

Version 1.6.1 (released 2025-01-23)

- assets: fix header + banner placement

Version 1.6.0 (released 2025-01-21)

- pipfile: upgrade dependencies

Version 1.5.0 (released 2025-01-20)

- conf: update stats to yearly
- views: register custom index page
- identifiers: register legacy cds id

Version 1.4.0 (released 2024-12-20)

- communities-records: set the config identical to global records search

Version 1.3.1 (released 2024-12-20)

- ui: move main banner below the navbar in the header

Version 1.3.0 (released 2024-12-19)

- stats: add new fields to differentiate migrated statistic events

Version 1.2.1 (released 2024-12-17)

- affiliationsSuggestions: Fix display of CERN authors info

Version 1.2.0 (released 2024-12-16)

- doi: add support for optional DOI
- analytics: add matomo scripts

Version 1.1.0 (released 2024-12-13)

- names: add internal_id
- installation: upgrade invenio-vocabularies
- config: remove optional dois
- installation: upgrade invenio-preservation-sync

Version 1.0.24 (released 2024-12-12)

- released on maint branch!

Version 1.0.23 (released 2024-12-09)

- affiliations: add missing affiliations from migration
- global: update Pipfiled

Version 1.0.22 (released 2024-12-03)

- global: update Pipfile
- update footer.html
- config: require users to upload files

Version 1.0.21 (released 2024-11-29)

- global: update invenio-accounts

Version 1.0.20 (released 2024-11-29)

- footer: fix duplication
- models: add new column to affiliations mapping table
- Pipfile: adds s3fs depdenency
- permissions: allow system process to manage files
- beams: convert cf to vocabulary
- vocabularies: harvest latest experiments
- legacy: Add redirection for collections
- legacy: Use system_identity for redirection
- setup: remove invenio-logging due to pypi issues
- config: make DOIs optional

Version 1.0.19 (released 2024-11-15)

- custom fields: add CERN fields
- docker: upgade opensearch images
- models: add migration affiliations table
- assets: move custom fields into basic info section
- views: Add files redirection for legacy recids
- upload: hide CERN section fields
- config: add beams CF and reorganize CF sections
- custom fields ui: add sorting by title
- gobal: integrates invenio-cern-sync and jobs
- names: sync CERN authors into names


Version 1.0.18 (released 2024-10-10)

- package-lock: bump RSK version

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
