---
id: alembic-migrations
name: Database models and Alembic migrations
paths:
  - "site/cds_rdm/alembic/**"
  - "site/cds_rdm/**/models.py"
---

- Every change to a SQLAlchemy model in a `models.py` (new table or column,
  type, nullability, index, constraint) needs a matching Alembic revision in
  `site/cds_rdm/alembic/`. Flag model changes that have no migration.
- Revisions use a timestamp-style `revision` id and must set `down_revision`
  to the current head of the `cds_rdm` branch. Two revisions pointing at the
  same parent create a second head and break `invenio alembic upgrade`. When a
  migration depends on upstream tables, set `depends_on` to the upstream
  revision (see the committee approval enrollment migration for an example).
- `downgrade()` must exactly reverse `upgrade()`. A `pass` downgrade needs a
  justification.
- Migrations run against a large production PostgreSQL database. Flag adding a
  `NOT NULL` column without a server default or backfill, full-table rewrites,
  and index creation on big tables that should be batched or done
  concurrently.
- Data migrations must not import application services or models that can
  change later. Use `op` / `sa.table()` with an explicit column subset.
- New model modules must be registered under `invenio_db.models` in
  `site/pyproject.toml`.
