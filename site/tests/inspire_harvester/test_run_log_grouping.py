# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Tests for lightweight harvester run log grouping.

Shapes covered here match stable writer/transformer messages and the
datastream skip wrappers from invenio-vocabularies.
"""

from cds_rdm.inspire_harvester.reports.runs.logs import group_log_hits


def _hit(message, level="ERROR", **extra):
    source = {"message": message, "level": level}
    source.update(extra)
    return source


def _group_titles(hits):
    grouped_issues, _other, _errors, _warnings = group_log_hits(hits)
    return [(issue["title"], issue["count"]) for issue in grouped_issues]


def test_writer_validation_messages_group_by_detail():
    hits = [
        _hit(
            "[INSPIRE#1] Error while processing entry: "
            "Record validation failed: metadata.title: Required."
        ),
        _hit(
            "[INSPIRE#2] Error while processing entry: "
            "Record validation failed: metadata.title: Required."
        ),
        _hit(
            "[INSPIRE#3] Validation error while processing entry: "
            "{0: {'affiliations': ['Not a valid list.']}}"
        ),
    ]
    titles = dict(_group_titles(hits))
    assert titles["metadata.title: required."] == 2
    assert titles["{0: {'affiliations': ['not a valid list.']}}"] == 1


def test_stable_writer_errors_group_together():
    hits = [
        _hit("[INSPIRE#111] Multiple records match."),
        _hit("[INSPIRE#222] Multiple records match."),
        # Indexed ERROR lines that still appended CDS ids (pre-fix harvest).
        _hit(
            "[INSPIRE#333] Multiple records match. CDS ids: 01rj6-zm861, 0y0x2-8a795"
        ),
        _hit(
            "[INSPIRE#444] Multiple records match. CDS ids: 0znka-eae04, 10zx7-rza90"
        ),
        _hit("[INSPIRE#1] File checksum mismatch."),
        _hit("[INSPIRE#2] File checksum mismatch."),
    ]
    titles = dict(_group_titles(hits))
    assert titles["multiple records match."] == 4
    assert titles["file checksum mismatch."] == 2


def test_skipped_entry_logs_split_by_stable_inner_reason():
    hits = [
        _hit("Skipping 3 transformed entries with errors.", level="WARNING"),
        _hit(
            "Skipped entry with errors: "
            "['[INSPIRE#1601699] Unexpected schema in external_system_identifiers.']",
            level="ERROR",
        ),
        _hit(
            "Skipped entry with errors: "
            "['[INSPIRE#1686691] Unexpected schema in external_system_identifiers.']",
            level="ERROR",
        ),
        _hit(
            "Skipped entry with errors: "
            "['[INSPIRE#2961010] More than 1 DOI was found.']",
            level="ERROR",
        ),
        _hit(
            "Skipped entry with errors: "
            "['[INSPIRE#579977] Publication date transformation failed.']",
            level="ERROR",
        ),
    ]
    titles = dict(_group_titles(hits))
    assert "Skipped entries" not in titles
    assert titles["unexpected schema in external_system_identifiers."] == 2
    assert titles["more than 1 doi was found."] == 1
    assert titles["publication date transformation failed."] == 1

    grouped_issues, other_lines, error_count, warning_count = group_log_hits(hits)
    assert other_lines == []
    assert error_count == 3
    assert warning_count == 0
    assert len(grouped_issues) == 3

    schema_bucket = next(
        issue for issue in grouped_issues if "unexpected schema" in issue["title"]
    )
    assert schema_bucket["records"] == ["1601699", "1686691"]
    assert schema_bucket["count"] == 2


def test_skip_summary_lines_are_omitted_from_grouped_report():
    hits = [
        _hit("Skipping 13 transformed entries with errors.", level="WARNING"),
        _hit("Skipping 21 transformed entries with errors.", level="WARNING"),
        _hit(
            "Skipped entry with errors: "
            "['[INSPIRE#1] More than 1 DOI was found.']",
            level="ERROR",
        ),
    ]
    grouped_issues, other_lines, error_count, warning_count = group_log_hits(hits)
    assert other_lines == []
    assert len(grouped_issues) == 1
    assert grouped_issues[0]["title"] == "more than 1 doi was found."
    assert grouped_issues[0]["records"] == ["1"]
    assert error_count == 1
    assert warning_count == 0


def test_info_lines_stay_in_other_lines():
    hits = [
        _hit("[INSPIRE#1] New draft is created (aaaaa-bb111).", level="INFO"),
        _hit("[INSPIRE#2] Draft bbbbb-cc222 published successfully.", level="INFO"),
    ]
    grouped_issues, other_lines, error_count, warning_count = group_log_hits(hits)
    assert grouped_issues == []
    assert len(other_lines) == 2
    assert error_count == 0
    assert warning_count == 0


def test_duplicate_hits_are_deduplicated():
    message = "[INSPIRE#777] More than 1 DOI was found."
    grouped_issues, _other, _errors, _warnings = group_log_hits(
        [_hit(message), _hit(message)]
    )
    assert len(grouped_issues) == 1
    assert len(grouped_issues[0]["entries"]) == 1


def test_vocabulary_warnings_group_by_vocabulary_not_term():
    hits = [
        _hit(
            "[INSPIRE#1] Vocabulary term not found in 'experiments'. | details: term=x-062",
            level="WARNING",
        ),
        _hit(
            "[INSPIRE#2] Vocabulary term not found in 'experiments'. | details: term=ion",
            level="WARNING",
        ),
        _hit(
            "[INSPIRE#3] Vocabulary term not found in 'accelerators'. | details: term=nq-052",
            level="WARNING",
        ),
    ]
    titles = dict(_group_titles(hits))
    assert titles["vocabulary term not found in 'experiments'."] == 2
    assert titles["vocabulary term not found in 'accelerators'."] == 1


def test_legacy_vocabulary_warnings_still_group():
    hits = [
        _hit(
            "[INSPIRE#1] vocabulary term 'x-062' not found in 'experiments'",
            level="WARNING",
        ),
        _hit(
            "[INSPIRE#2] vocabulary term 'ion' not found in 'experiments'",
            level="WARNING",
        ),
        _hit(
            "[INSPIRE#3] vocabulary term 'nq-052' not found in 'accelerators'",
            level="WARNING",
        ),
    ]
    titles = dict(_group_titles(hits))
    assert titles["vocabulary term not found in 'experiments'."] == 2
    assert titles["vocabulary term not found in 'accelerators'."] == 1


def test_details_suffix_is_ignored_for_group_title():
    hits = [
        _hit("[INSPIRE#1] DOI validation failed. | details: doi=bad-1"),
        _hit("[INSPIRE#2] DOI validation failed. | details: doi=bad-2"),
    ]
    titles = dict(_group_titles(hits))
    assert titles["doi validation failed."] == 2
