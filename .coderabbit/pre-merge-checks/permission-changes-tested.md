---
id: permission-changes-tested
name: Permission changes are tested
mode: warning
report: platform
paths:
  - "site/cds_rdm/permissions.py"
  - "site/cds_rdm/generators.py"
  - "site/cds_rdm/administration/permissions.py"
  - "site/cds_rdm/**/services/permissions.py"
  - "site/tests/**"
---

Pass when the PR doesn't change any permission policy or generator. These live
in `site/cds_rdm/permissions.py`, `site/cds_rdm/generators.py`,
`site/cds_rdm/administration/permissions.py` and the feature services'
`site/cds_rdm/**/services/permissions.py` (for example
`CLCSyncPermissionPolicy` and `CommitteeApprovalEnrollmentPermissionPolicy`).

If it does, pass only when the PR also adds or updates tests under
`site/tests/` that exercise each changed action, with at least one identity
that should be allowed and one that should be denied.

Fail otherwise. In the failure message, list the changed actions and say who
gains or loses access through each one.
