# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""CDS-RDM migration rules module."""

import datetime

import pycountry
from dojson.errors import IgnoreKey
from dojson.utils import filter_values, flatten, force_list

from ..models.note import model
from .contributors import extract_json_contributor_ids, get_contributor_role
from .dates import get_week_start
from .errors import UnexpectedValue
from .quality.decorators import (
    filter_list_values,
    for_each_value,
    require,
    strip_output,
)
from .quality.parsers import clean_str


@model.over("legacy_recid", "^001")
def recid(self, key, value):
    """Record Identifier."""
    self["recid"] = value
    return int(value)


@model.over("agency_code", "^003")
def agency_code(self, key, value):
    """Control number identifier."""
    if isinstance(value, str):
        return value
    else:
        raise IgnoreKey("agency_code")


@model.over("_created", "(^916__)")
@require(["w"])
def created(self, key, value):
    """Translates created information to fields."""
    date_values = value.get("w")
    if not date_values or not date_values[0]:
        return datetime.date.today().isoformat()
    date = min(date_values)
    try:
        if date:
            if not (100000 < int(date) < 999999):
                raise IgnoreKey
                # raise UnexpectedValue("Wrong date format", field=key, subfield='w')
            year, week = str(date)[:4], str(date)[4:]
            date = get_week_start(int(year), int(week))
            if date < datetime.date.today():
                return date.isoformat()
            else:
                return datetime.date.today().isoformat()
    except ValueError:
        return datetime.date.today().isoformat()


@model.over("title", "^245__")
def title(self, key, value):
    """Translates title."""
    return value.get("a", "TODO")


@model.over("creators", "^100__")
@for_each_value
@require(["a"])
def creators(self, key, value):
    """Translates the creators field."""
    role = get_contributor_role("e", value.get("e", "author"))

    contributor = {
        "person_or_org": {
            "type": "personal",
            "name": value.get("name") or value.get("a"),
            "identifiers": extract_json_contributor_ids(value),
        }
    }
    if role:
        contributor.update({"role": {"id": role}})  # VOCABULARY ID

    return contributor


@model.over("contributors", "^700__")
@for_each_value
@require(["a"])
def contributors(self, key, value):
    """Translates contributors."""
    return creators(self, key, value)


@model.over("description", "^520__")
@strip_output
def abstract(self, key, value):
    """Translates abstracts fields."""
    return value.get("a", "")


@model.over("languages", "^041__")
@for_each_value
@require(["a"])
@strip_output
def languages(self, key, value):
    """Translates languages fields."""
    lang = clean_str(value.get("a"))
    if lang:
        lang = lang.lower()
    try:
        return pycountry.languages.lookup(lang).alpha_3.upper()
    except (KeyError, AttributeError, LookupError):
        raise UnexpectedValue(field=key, subfield="a")


@model.over("subjects", "^693__")
@require(["a"])
@filter_list_values
def subjects(self, key, value):
    """Translates languages fields."""
    _subjects = self.get("subjects", [])
    subject_a = value.get("a")
    subject_e = value.get("e")

    if subject_a:
        obj = {"subject": subject_a}
        if obj not in _subjects:
            _subjects.append(obj)
    if subject_e:
        obj = {"subject": subject_e}
        if obj not in _subjects:
            _subjects.append(obj)


@model.over("communities", "^980__")
@require(["a"])
def communities(self, key, value):
    """Translates communities."""
    return ["cms-notes"]
