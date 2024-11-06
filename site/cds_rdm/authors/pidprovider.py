# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2024 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.


"""CDS RDM PID providers."""

from __future__ import absolute_import

from base32_lib import base32
from invenio_pidstore.models import PIDStatus
from invenio_pidstore.providers.base import BaseProvider


class AuthorIdProvider(BaseProvider):
    """Author identifier provider."""

    pid_type = "autid"
    """Type of persistent identifier."""

    pid_provider = None
    """Provider name.

    The provider name is not recorded in the PID since the provider does not
    provide any additional features besides creation of author ids.
    """

    default_status_with_obj = PIDStatus.REGISTERED
    """Author IDs are by default registered immediately.

    Default: :attr:`invenio_pidstore.models.PIDStatus.REGISTERED`
    """

    default_status = PIDStatus.RESERVED
    """Author IDs with an object are by default reserved.

    Default: :attr:`invenio_pidstore.models.PIDStatus.RESERVED`
    """

    @classmethod
    def generate_id(cls):
        """Generate author id."""
        _id = base32.generate(length=10, split_every=0, checksum=True)
        return "cds:a:" + _id

    @classmethod
    def create(cls, object_type=None, object_uuid=None, **kwargs):
        """Create a new record identifier.

        Note: if the object_type and object_uuid values are passed, then the
        PID status will be automatically setted to
        :attr:`invenio_pidstore.models.PIDStatus.REGISTERED`.

        For more information about parameters,
        see :meth:`invenio_pidstore.providers.base.BaseProvider.create`.

        :param object_type: The object type. (Default: None.)
        :param object_uuid: The object identifier. (Default: None).
        :param kwargs: dict to hold generated pid_value and status. See
            :meth:`invenio_pidstore.providers.base.BaseProvider.create` extra
            parameters.
        :returns: A :class:`RecordIdProviderV2` instance.
        """
        assert "pid_value" not in kwargs

        kwargs["pid_value"] = cls.generate_id()
        kwargs.setdefault("status", cls.default_status)

        if object_type and object_uuid:
            kwargs["status"] = cls.default_status_with_obj

        return super(AuthorIdProvider, cls).create(
            object_type=object_type, object_uuid=object_uuid, **kwargs
        )
