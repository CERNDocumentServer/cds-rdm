---
id: inspire-harvester
name: INSPIRE harvester pipeline
paths:
  - "site/cds_rdm/inspire_harvester/**"
  - "site/cds_rdm/harvester_download/**"
  - "site/cds_rdm/harvester_runs/**"
  - "site/cds_rdm/administration/harvester_reports.py"
  - "site/tests/inspire_harvester/**"
---

The harvester is an `invenio_jobs` job (`ProcessInspireHarvesterJob`) that
reads INSPIRE literature records and creates or updates CDS records as a
system/harvester identity. The pipeline is:

1. `reader.py` fetches pages from the INSPIRE API.
2. `transform/` maps INSPIRE JSON to RDM metadata through the mappers in
   `transform/mappers/` (basic metadata, contributors, identifiers, funding,
   custom fields, files, and per document type: article, preprint, thesis),
   plus `policies.py` and `resource_types.py`.
3. `load/` matches existing CDS records (`matcher.py`), validates, builds
   drafts and attaches files.
4. `update/` is a field-wise update engine that changes existing records only
   when harvested data differs.
5. `writer.py` and `reports/` log the run and expose downloadable reports.

Review for:

- **Matching correctness.** False-positive matches overwrite someone else's
  record, and false negatives create duplicates. Check identifier matching (DOI,
  arXiv, INSPIRE ID, CDS ID, report numbers) for normalisation (case, prefixes,
  versions such as `v2`) and for handling of multiple and tombstoned/deleted
  hits.
- **Safe updates.** The harvester must not clobber curator edits it doesn't own,
  must not update restricted records or records with an open draft, and must
  skip updates when nothing changed. A new update field needs a comparison
  that ignores ordering and formatting noise.
- **Failure isolation.** One bad INSPIRE entry must be logged with its INSPIRE
  ID and a clear reason, then skipped. It must not abort the whole run or leave
  an orphan draft or file bucket.
- **Mappers** must tolerate missing or partial INSPIRE fields. No unguarded
  `[0]` or `["key"]` on optional data. Values must map onto controlled
  vocabularies (resource types, subjects, experiments, accelerators) through
  the vocabulary service, not free text.
- **Files.** Check size and checksum handling and the cleanup of partial
  uploads. Avoid loading whole PDFs into memory.
- **Tests.** Mapper and update changes need a fixture-driven test under
  `site/tests/inspire_harvester/` using a JSON sample in `data/`. Prefer
  extending an existing sample over adding a large new one.
