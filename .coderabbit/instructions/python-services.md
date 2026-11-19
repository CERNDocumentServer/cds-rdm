---
id: python-services
name: Services, components, tasks and jobs
paths:
  - "site/cds_rdm/**/*.py"
exclude:
  - "site/cds_rdm/alembic/**"
  - "site/cds_rdm/inspire_harvester/**"
---

InvenioRDM business logic is composed, not inherited:

- Behaviour hooks into record/draft lifecycles through `ServiceComponent`
  subclasses (`create`, `update_draft`, `publish`, `submit_record`, …) wired up
  through service config. Flag logic that bypasses the service layer by writing
  to `record.model`, calling `db.session.commit()` directly, or reindexing by
  hand inside a request or service call. Writes go through the service with a
  unit of work (`uow` / `@unit_of_work`), and indexing is a
  `RecordIndexOp`/`RecordCommitOp` on that unit of work.
- Services must call `self.require_permission(identity, action, ...)` or
  `check_permission` before reading or mutating. A new service method without a
  permission check is a security bug.
- Use `system_identity` only in background or system flows (tasks, jobs,
  harvester, CLI). Never use it in request handlers to skip a permission check
  for a real user.
- Validation errors raised from components should be
  `ValidationError`/`ValidationErrorWithMessageAsList` and should carry a
  field path, so the deposit form can show them inline.
- Search queries built by hand must escape user input. Prefer the service's
  `search(params=...)` over building raw OpenSearch DSL.

Celery tasks (`tasks.py`) and `invenio_jobs` jobs (`jobs.py`):

- Must be idempotent and safe to retry. Watch for partial writes when a loop
  fails halfway through.
- Must not hold large result sets in memory. Use `scan`/pagination.
- Long-running jobs should log progress through the job/run logger, not
  `print`.
- External calls (LDAP, CERN auth, DataCite, INSPIRE, EOS) need timeouts and
  explicit error handling. Credentials come from config, never from literals.

REST resources and views:

- Resources follow the `Resource`/`ResourceConfig` pattern with
  `request_view_args`/`request_extra_args` parsers. Flag unvalidated
  `request.args`/`request.json` access.
- New blueprints must be registered as entry points in `site/pyproject.toml`.
