---
id: vocabularies-fixtures
name: Vocabulary and fixture data
paths:
  - "app_data/**"
---

`app_data/vocabularies/*.yaml` are controlled vocabularies (experiments,
accelerators, beams, committees, departments, awards, funders, subjects, resource
types, …) loaded with `invenio rdm-records fixtures`. Their ids end up in record
metadata and in the search index.

- **Renaming or removing an existing `id` needs a migration recipe in the PR
  description** (the old-to-new mapping and how existing records get updated),
  because published records reference it. Renaming the title or adding an
  alias needs no migration.
- New entries must have a unique `id` within the file. Look for duplicates or
  near-duplicates (case, whitespace, acronym versus full name) of existing
  entries.
- Keep the file's existing structure: `title` per language (at least `en`),
  `props`, `tags`, aliases and hierarchy keys used by neighbouring entries. For
  hierarchical vocabularies (subjects, departments), parents must exist.
- Award entries must reference an existing funder id. Award and funder
  identifiers (ROR, grant number, CORDIS) must be well-formed.
- Fixtures only load into empty instances. For production, say in the PR how
  the change will be applied (an update command or job). Flag vocabulary PRs
  that don't mention it.
- `app_data/pages/*.html` are static legal/policy pages. Check links and avoid
  inline scripts.
