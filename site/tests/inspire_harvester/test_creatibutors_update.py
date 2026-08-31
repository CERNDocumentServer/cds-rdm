# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""CreatibutorsFieldUpdate matching tests."""

from cds_rdm.inspire_harvester.update.fields.creatibutors import CreatibutorsFieldUpdate

PATH = "metadata.creators"


def _person(family="", given="", name="", orcid=None):
    """Build a creator entry."""
    person = {
        "type": "personal",
        "family_name": family,
        "given_name": given,
        "name": name or ", ".join(part for part in (family, given) if part),
    }
    if orcid:
        person["identifiers"] = [{"scheme": "orcid", "identifier": orcid}]
    return {"person_or_org": person}


def _merge(current_creators, incoming_creators):
    strategy = CreatibutorsFieldUpdate(strict=True)
    return strategy.update(
        {"metadata": {"creators": current_creators}},
        {"metadata": {"creators": incoming_creators}},
        PATH,
        ctx=None,
    )


def test_name_key_uses_family_given_and_full_name():
    """Matching is on the full name tuple, not given name alone."""
    keys = CreatibutorsFieldUpdate()._keys(
        _person(family="Rossi", given="Anna", name="Rossi, Anna")
    )

    assert ("name", "rossi", "anna", "rossi, anna") in keys


def test_same_given_name_different_family_is_not_merged():
    """Two people who share a given name are not treated as one person."""
    result = _merge(
        [_person(family="Rossi", given="Anna", name="Rossi, Anna")],
        [_person(family="Bianchi", given="Anna", name="Bianchi, Anna")],
    )

    stored = result.updated["metadata"]["creators"][0]["person_or_org"]
    assert stored["family_name"] == "Rossi"
    assert [w.kind for w in result.warnings] == ["new_creator"]


def test_stored_name_only_gains_orcid_from_inspire():
    """Stored author keyed by name still matches incoming ORCID."""
    result = _merge(
        [_person(family="Doe", given="John", name="Doe, John")],
        [
            _person(
                family="Doe",
                given="John",
                name="Doe, John",
                orcid="0000-0002-1825-0097",
            )
        ],
    )

    assert result.warnings == []
    assert result.updated["metadata"]["creators"][0]["person_or_org"]["identifiers"] == [
        {"scheme": "orcid", "identifier": "0000-0002-1825-0097"}
    ]


def test_same_name_different_orcids_are_not_merged():
    """Two people with the same name and different ORCIDs stay separate."""
    result = _merge(
        [
            _person(
                family="Smith",
                given="John",
                name="Smith, John",
                orcid="0000-0001-0000-0001",
            )
        ],
        [
            _person(
                family="Smith",
                given="John",
                name="Smith, John",
                orcid="0000-0002-0000-0002",
            )
        ],
    )

    assert [w.kind for w in result.warnings] == ["new_creator"]
    stored = result.updated["metadata"]["creators"][0]["person_or_org"]
    assert stored["identifiers"] == [
        {"scheme": "orcid", "identifier": "0000-0001-0000-0001"}
    ]
