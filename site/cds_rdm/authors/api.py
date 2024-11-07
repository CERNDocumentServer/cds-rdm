# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2024 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""CDS RDM api."""

from .models import AuthorMetadata
from invenio_records.systemfields import ConstantField, ModelField
from invenio_records_resources.records.api import Record
from invenio_records_resources.records.systemfields import PIDField
from .pidprovider import AuthorIdProvider

class Author(Record):
    """An author record."""

    # Configuration
    model_cls = AuthorMetadata

    # System fields
    schema = ConstantField(
        "$schema",
        "local://records/authors-v1.0.0.json",
    )

    user_id = ModelField()

    pid = PIDField(
        "id",
        provider=AuthorIdProvider,
    )

    @classmethod
    def get_record_by_user_id(cls, user_id):
        """Retrieve a record by user id."""
        obj = cls.model_cls.query.filter_by(user_id=user_id).one()
        return cls(obj.data, model=obj)
