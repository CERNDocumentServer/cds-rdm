---
id: configuration-and-deployment
name: Instance configuration, dependencies and deployment
paths:
  - "invenio.cfg"
  - "site/cds_rdm/config.py"
  - "pyproject.toml"
  - "site/pyproject.toml"
  - "Dockerfile"
  - "docker/**"
  - "docker-compose*.yml"
  - "docker-services.yml"
  - ".github/workflows/**"
---

- `invenio.cfg` is shared by local development and deployments. Production
  values come from `INVENIO_*` environment variables. Flag real secrets, tokens,
  passwords, hostnames or internal CERN endpoints added as literals. The existing
  `CHANGE_ME` / empty-string placeholders are intentional.
- Changes to permission policies, record or file settings, OAI-PMH, DataCite/DOI
  minting, search or Celery beat schedules have production impact. Ask for the
  intended behaviour to be stated in the PR.
- Overriding an upstream config key: check that the name exists in the
  installed `invenio-*` version, since a typo silently has no effect, and that
  it isn't already set elsewhere in the file.
- Dependency changes in `pyproject.toml` must come with an updated `uv.lock`
  (CI runs `uv sync --locked`). JS dependency changes need an updated
  `pnpm-lock.yaml` (CI runs `pnpm install --frozen-lockfile`). Upgrades of
  `invenio-app-rdm` or other `invenio-*` packages are major-version sensitive.
  Ask whether upstream upgrade notes or migrations apply.
- Python targets 3.14 (see CI). Don't suggest compatibility shims for older
  versions.
- Dockerfile/compose: pin base image versions, don't bake in secrets, and keep
  layer order cache-friendly.
