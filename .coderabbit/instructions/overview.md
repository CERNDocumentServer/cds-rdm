---
id: cds-rdm-overview
name: CDS-RDM overview and general rules
---

CDS-RDM is the CERN Document Server **instance** built on InvenioRDM. It is not
a library. The repository is a uv workspace: the root `pyproject.toml` pulls in
`invenio-app-rdm`, and `site/` is a workspace member that ships the `cds_rdm`
package.

Where code belongs:

- `site/cds_rdm/` holds instance Python code: service components, permission
  generators, custom fields, request types, Celery tasks, jobs, CLI, the INSPIRE
  harvester, CLC sync, committee approval and legacy redirects.
- `invenio.cfg` holds instance configuration. `site/cds_rdm/config.py` holds
  config defaults for the `cds_rdm` extensions.
- `app_data/` holds fixtures and controlled vocabularies.
- `assets/` and `templates/` at the root hold UI overrides of upstream
  packages. `site/cds_rdm/assets/` and `site/cds_rdm/templates/` hold UI that
  belongs to `cds_rdm` features.
- Entry points (blueprints, jobs, tasks, request types, idutils schemes, alembic,
  models, admin views, access actions) are registered in `site/pyproject.toml`.
  Flag a new plugin of one of these kinds (a blueprint, job, task module,
  request type, model, admin view, access action, …) that isn't registered
  there, because Invenio will never load it. Ordinary helper modules that are
  imported normally need no entry point.

When reviewing:

- If a change works around generic InvenioRDM behaviour (records, drafts,
  communities, requests, vocabularies), ask whether it belongs upstream in an
  `invenio-*` package. Monkeypatching upstream classes is a red flag. Prefer
  config, components, generators and overridable hooks.
- Every source file keeps its GPL-2.0 license header with the CERN copyright
  line. Edited files extend the year range.
- Python formatting is `black` (88-character lines) and import ordering is
  `isort` with `profile = black`. Both run through pytest (`--black --isort`),
  so CI fails on violations. Docstrings are checked by `pydocstyle`, with D401
  and D403 ignored, so public modules, classes and functions need one. Do not
  suggest ruff, flake8 or pylint rules, or style changes that conflict with
  black or isort.
- User-facing strings go through `invenio_i18n` (`_` / `lazy_gettext`) in
  Python and `i18next` in JS. Flag hard-coded English in the UI.
- Do not comment on formatting that `black`/`ruff`/`eslint` already enforce.
