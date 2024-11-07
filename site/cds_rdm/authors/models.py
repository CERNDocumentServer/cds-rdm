# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2024 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""CDS RDM models."""

from invenio_db import db
from invenio_records.models import RecordMetadataBase


class AuthorMetadata(db.Model, RecordMetadataBase):
    """Author metadata model."""

    __tablename__ = "authors_metadata"

    user_id = db.Column(db.Integer)