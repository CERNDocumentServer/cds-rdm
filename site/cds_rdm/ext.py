# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the GPL-2.0 License; see LICENSE file for more details.

"""CDS-RDM module."""
from datetime import datetime

from flask import current_app
from invenio_jobs.logging.jobs import ContextAwareOSHandler, job_context
from invenio_jobs.services import JobLogEntrySchema
from invenio_search import current_search_client
from invenio_search.utils import prefix_index

from cds_rdm.clc_sync.resources.config import CLCSyncResourceConfig
from cds_rdm.clc_sync.resources.resource import CLCSyncResource
from cds_rdm.clc_sync.resources.utils import get_clc_sync_entry
from cds_rdm.clc_sync.services.config import CLCSyncServiceConfig
from cds_rdm.clc_sync.services.service import CLCSyncService
from cds_rdm.harvester_download.resources import (
    HarvesterDownloadResource,
    HarvesterDownloadResourceConfig,
)

from . import config
from .utils import evaluate_permissions
from .views import get_linked_records_search_query


class CDSContextAwareOSHandler(ContextAwareOSHandler):
    """Job log handler that preserves selected structured fields."""

    _extra_fields = (
        "entry_id",
        "inspire_id",
        "record_pid",
        "report_group_key",
        "report_kind",
        "report_reason",
        "skip_sentry",
    )

    def enrich_log(self, record):
        """Enrich log record with context and supported extra fields."""
        context = dict(job_context.get())
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "context": context,
        }
        serialized_data = JobLogEntrySchema().load(log_data)
        for field_name in self._extra_fields:
            value = getattr(record, field_name, None)
            if value is not None:
                serialized_data[field_name] = value
        return serialized_data

    def index_in_os(self, log_data):
        """Send log data to OpenSearch."""
        full_index_name = prefix_index(current_app.config["JOBS_LOGGING_INDEX"])
        current_search_client.index(index=full_index_name, body=log_data)


class CDS_RDM_App(object):
    """CDS-RDM App."""

    def __init__(self, app):
        """Constructor."""
        if app:
            self.init_config(app)
            self.init_app(app)

    def init_config(self, app):
        """Initialize configuration."""
        for k in dir(config):
            app.config.setdefault(k, getattr(config, k))

    def init_app(self, app):
        """Flask application initialization."""
        self.init_services(app)
        self.init_resources(app)
        self.init_job_logging(app)
        app.jinja_env.globals["get_clc_sync_entry"] = get_clc_sync_entry
        app.jinja_env.globals["evaluate_permissions"] = evaluate_permissions
        # Register filter for building linked records search query
        app.jinja_env.filters["get_linked_records_search_query"] = (
            get_linked_records_search_query
        )
        return app

    def init_services(self, app):
        """Initialize the services for banners."""
        self.clc_sync_service = CLCSyncService(config=CLCSyncServiceConfig)

    def init_resources(self, app):
        """Initialize the resources for banners."""
        self.clc_sync_resource = CLCSyncResource(
            service=self.clc_sync_service,
            config=CLCSyncResourceConfig,
        )
        self.harvester_download_resource = HarvesterDownloadResource(
            config=HarvesterDownloadResourceConfig,
        )

    def init_job_logging(self, app):
        """Replace the default jobs log handler with the CDS-aware variant."""
        handlers = list(app.logger.handlers)
        for handler in handlers:
            if type(handler) is ContextAwareOSHandler:
                app.logger.removeHandler(handler)

        if app.config.get("JOBS_LOGGING"):
            os_handler = CDSContextAwareOSHandler()
            os_handler.setLevel(app.config["JOBS_LOGGING_LEVEL"])
            app.logger.addHandler(os_handler)


class CDS_RDM_UI(object):
    """CDS-RDM extension."""

    def __init__(self, app=None):
        """Extension initialization."""
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Flask application initialization."""
        extension = CDS_RDM_App(app)
        app.extensions["cds-rdm"] = extension
        return extension


class CDS_RDM_REST(object):
    """CDS-RDM REST extension."""

    def __init__(self, app=None):
        """Extension initialization."""
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Flask application initialization."""
        extension = CDS_RDM_App(app)
        app.extensions["cds-rdm"] = extension
        return extension
