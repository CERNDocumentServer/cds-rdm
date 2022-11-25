# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""CDS-RDM migration decorators."""

import functools

from dojson.errors import IgnoreKey, IgnoreItem

from cds_rdm.migration.transform.xml_processing.errors import MissingRequiredField


def strip_output(fn_decorated):
    """Decorator cleaning output values of trailing and following spaces."""

    def proxy(self, key, value, **kwargs):
        res = fn_decorated(self, key, value, **kwargs)
        if not res:
            raise IgnoreKey(key)
        if isinstance(res, str):
            return res.strip()
        elif isinstance(res, list):
            cleaned = [elem.strip() for elem in res if elem]
            if not cleaned:
                raise IgnoreKey(key)
            return cleaned
        else:
            return res

    return proxy


def require(subfields):
    """Mark required subfields in a MARC field."""

    def the_decorator(fn_decorated):
        def proxy(self, key, value, **kwargs):
            for subfield in subfields:
                value.get(subfield)
                if not subfield:
                    raise MissingRequiredField(field=key, subfield=subfield)
            res = fn_decorated(self, key, value, **kwargs)
            return res
        return proxy

    return the_decorator


def for_each_value(f, duplicates=False):
    """Apply function to each item."""
    # Extends values under same name in output.  This should be possible
    # because we are already expecting list.
    setattr(f, '__extend__', True)

    @functools.wraps(f)
    def wrapper(self, key, values, **kwargs):
        parsed_values = []

        if not isinstance(values, (list, tuple, set)):
            values = [values]

        for value in values:
            try:
                if not duplicates and value not in parsed_values:
                    parsed_values.append(f(self, key, value, **kwargs))
                elif duplicates:
                    parsed_values.append(f(self, key, value, **kwargs))
            except IgnoreItem:
                continue

        return parsed_values
    return wrapper


def filter_empty_dict_values(f):
    """Remove None values from dictionary."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        out = f(*args, **kwargs)
        return dict((k, v) for k, v in out.items() if v)
    return wrapper


def filter_list_values(f):
    """Remove None and blank string values from list of dictionaries."""

    @functools.wraps(f)
    def wrapper(self, key, value, **kwargs):
        out = f(self, key, value)
        if out:
            clean_list = [
                dict((k, v) for k, v in elem.items() if v)
                for elem in out
                if elem
            ]
            clean_list = [elem for elem in clean_list if elem]
            if not clean_list:
                raise IgnoreKey(key)
            return clean_list
        else:
            raise IgnoreKey(key)

    return wrapper
