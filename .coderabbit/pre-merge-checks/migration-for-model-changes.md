---
id: migration-for-model-changes
name: Model changes have a migration
mode: warning
report: platform
paths:
  - "site/cds_rdm/**/models.py"
  - "site/cds_rdm/alembic/**"
---

Pass when the PR doesn't change any SQLAlchemy model in
`site/cds_rdm/**/models.py`.

If it adds, removes or alters a table, column, type, nullability, index or
constraint, pass only when all of the following hold:

1. The PR adds a new revision file under `site/cds_rdm/alembic/` that applies
   the same schema change.
2. Its `down_revision` points at the previous head of the `cds_rdm` alembic
   branch, and no other revision shares that `down_revision`.
3. `downgrade()` reverses `upgrade()` and isn't an empty `pass`.

Fail otherwise, naming the model change that has no migration and the missing
items from the list above.
