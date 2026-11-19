---
id: tests
name: Test suite
paths:
  - "site/tests/**"
  - "conftest.py"
---

- Tests run with `pytest-invenio` against real PostgreSQL and OpenSearch
  (`site/run-tests.sh`). Prefer the shared fixtures in `site/tests/conftest.py`
  (app config, users/identities, vocabularies, communities, minimal records)
  over building app state by hand.
- External services (DataCite, Crossref, INSPIRE, LDAP/Keycloak) must be faked
  or mocked. See `fake_datacite_client.py` and `fake_crossref_client.py`. Flag a
  test that connects to an external service. Connections to the local services
  the test runner starts (PostgreSQL, OpenSearch, Redis, RabbitMQ) are expected.
- After writes, tests that query search must refresh the index (for example
  `Record.index.refresh()`), or they will be flaky.
- Permission changes need both a positive and a negative assertion.
- Name tests by behaviour and keep them independent. No reliance on test
  order or on state left by another module's fixtures.
