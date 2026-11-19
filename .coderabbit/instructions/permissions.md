---
id: permissions
name: Permissions and access generators
paths:
  - "site/cds_rdm/permissions.py"
  - "site/cds_rdm/generators.py"
  - "site/cds_rdm/administration/permissions.py"
  - "site/cds_rdm/requests/**"
  - "site/cds_rdm/committee_approval_enrollments/**"
  - "site/cds_rdm/clc_sync/services/**"
---

These files decide who can see and change records at CERN. Restricted and
embargoed content is a real data-leak risk, so review this area strictly.

- Policies are lists of `Generator`s per action (`can_read`, `can_update_draft`,
  `can_publish`, `can_manage_files`, …). For each changed action, state who
  **gains** access and who **loses** it. Treat any widening of `can_read`,
  `can_read_files`, `can_search` or `can_manage` as high-risk and call it out
  explicitly.
- A generator must implement `needs()` and, if used in search, `query_filter()`
  consistently. A generator that grants a need without the matching query
  filter, or the other way round, makes search results disagree with
  record-level access.
- `excludes()` is rarely the right tool. Check it isn't used to "fix" a
  `needs()` bug.
- Admins usually hold `superuser-access`, which bypasses most checks. Code that
  must constrain admins (for example the locked-files logic) has to say so
  explicitly. Don't let a refactor drop that.
- `SystemProcess` belongs only on actions the harvester, jobs or tasks perform.
- New `invenio_access` actions must be registered as entry points in
  `site/pyproject.toml`, and any role they rely on must exist (fixtures or an
  upgrade step).
- Request types (committee approval) need permissions for every request action
  (`create`, `submit`, `accept`, `decline`, `cancel`, `expire`, comment) and
  matching notification builders and templates.
- Ask for tests that cover both the allowed and the denied identity for every
  changed action.
