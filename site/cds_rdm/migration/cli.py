# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""CDS-RDM command line module."""

from pathlib import Path

import click

from cds_rdm.migration.streams import RecordStreamDefinition, UserStreamDefinition
from invenio_rdm_migrator.streams import Runner


@click.group()
def migration():
    pass


@migration.command()
def run():
    runner = Runner(
        stream_definitions=[
            RecordStreamDefinition,
            UserStreamDefinition,
        ],
        config_filepath=Path("site/cds_rdm/migration/streams.yaml").absolute(),
    )
    runner.run()
