# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Pytest fixtures."""

from collections import namedtuple

import pytest
from celery import current_app as current_celery_app
from flask import current_app
from flask_webpackext.manifest import (
    JinjaManifest,
    JinjaManifestEntry,
    JinjaManifestLoader,
)
from invenio_access.models import ActionRoles
from invenio_access.permissions import superuser_access, system_identity
from invenio_accounts import testutils
from invenio_accounts.models import Role
from invenio_administration.permissions import administration_access_action
from invenio_app import factory as app_factory
from invenio_cern_sync.users.profile import CERNUserProfileSchema
from invenio_communities.communities.records.api import Community
from invenio_communities.proxies import current_communities
from invenio_i18n import lazy_gettext as _
from invenio_pidstore.models import PersistentIdentifier, PIDStatus
from invenio_rdm_records.cli import create_records_custom_field
from invenio_rdm_records.config import (
    RDM_PARENT_PERSISTENT_IDENTIFIERS,
    RDM_PERSISTENT_IDENTIFIERS,
    RDM_RECORDS_IDENTIFIERS_SCHEMES,
    always_valid,
)
from invenio_records_resources.proxies import current_service_registry
from invenio_users_resources.records.api import UserAggregate
from invenio_vocabularies.config import (
    VOCABULARIES_DATASTREAM_READERS,
    VOCABULARIES_DATASTREAM_TRANSFORMERS,
    VOCABULARIES_DATASTREAM_WRITERS,
)
from invenio_vocabularies.config import (
    VOCABULARIES_NAMES_SCHEMES as DEFAULT_VOCABULARIES_NAMES_SCHEMES,
)
from invenio_vocabularies.contrib.awards.api import Award
from invenio_vocabularies.contrib.funders.api import Funder
from invenio_vocabularies.proxies import current_service as vocabulary_service
from invenio_vocabularies.records.api import Vocabulary

from cds_rdm.inspire_harvester.reader import InspireHTTPReader
from cds_rdm.inspire_harvester.transformer import InspireJsonTransformer
from cds_rdm.inspire_harvester.writer import InspireWriter
from cds_rdm.permissions import (
    CDSCommunitiesPermissionPolicy,
    CDSRDMRecordPermissionPolicy,
)
from cds_rdm.schemes import is_aleph, is_inspire, is_inspire_author, is_legacy_cds

pytest_plugins = ("celery.contrib.pytest",)


class MockJinjaManifest(JinjaManifest):
    """Mock manifest."""

    def __getitem__(self, key):
        """Get a manifest entry."""
        return JinjaManifestEntry(key, [key])

    def __getattr__(self, name):
        """Get a manifest entry."""
        return JinjaManifestEntry(name, [name])


class MockManifestLoader(JinjaManifestLoader):
    """Manifest loader creating a mocked manifest."""

    def load(self, filepath):
        """Load the manifest."""
        return MockJinjaManifest()


@pytest.fixture(scope="module")
def community_service(app):
    """Community service."""
    return current_communities.service


@pytest.fixture(scope="module")
def minimal_community():
    """Minimal community metadata."""
    return {
        "access": {
            "visibility": "public",
            "members_visibility": "public",
            "record_submission_policy": "open",
        },
        "slug": "public",
        "metadata": {
            "title": "My Community",
        },
    }


@pytest.fixture(scope="function")
def scientific_community(community_service, minimal_community):
    """Scientific community where Thesis should be submitted."""
    minimal_community["slug"] = "scc"
    minimal_community["title"] = "Scientific Community"
    c = community_service.create(system_identity, minimal_community)
    Community.index.refresh()
    current_app.config["CDS_CERN_SCIENTIFIC_COMMUNITY_ID"] = str(c.id)
    return c._record


@pytest.fixture(scope="module")
def app_config(app_config):
    """Mimic an instance's configuration."""
    app_config["REST_CSRF_ENABLED"] = True
    app_config["DATACITE_ENABLED"] = True
    app_config["DATACITE_PREFIX"] = "10.17181"
    app_config["OAUTH_REMOTE_APP_NAME"] = "cern"
    app_config["CERN_APP_CREDENTIALS"] = {
        "consumer_key": "CHANGE ME",
        "consumer_secret": "CHANGE ME",
    }
    app_config["VOCABULARIES_DATASTREAM_READERS"] = {
        **VOCABULARIES_DATASTREAM_READERS,
        "inspire-http-reader": InspireHTTPReader,
    }
    app_config["VOCABULARIES_DATASTREAM_TRANSFORMERS"] = {
        **VOCABULARIES_DATASTREAM_TRANSFORMERS,
        "inspire-json-transformer": InspireJsonTransformer,
    }
    app_config["VOCABULARIES_DATASTREAM_WRITERS"] = {
        **VOCABULARIES_DATASTREAM_WRITERS,
        "inspire-writer": InspireWriter,
    }

    app_config["RDM_PERSISTENT_IDENTIFIERS"] = RDM_PERSISTENT_IDENTIFIERS
    app_config["RDM_PERSISTENT_IDENTIFIERS"]["doi"]["required"] = False
    app_config["RDM_PARENT_PERSISTENT_IDENTIFIERS"] = RDM_PARENT_PERSISTENT_IDENTIFIERS
    app_config["RDM_PARENT_PERSISTENT_IDENTIFIERS"]["doi"]["required"] = False

    app_config["CERN_LDAP_URL"] = ""  # mock
    app_config["ACCOUNTS_USER_PROFILE_SCHEMA"] = CERNUserProfileSchema()
    app_config["COMMUNITIES_PERMISSION_POLICY"] = CDSCommunitiesPermissionPolicy
    app_config["RDM_PERMISSION_POLICY"] = CDSRDMRecordPermissionPolicy
    app_config["COMMUNITIES_ALLOW_RESTRICTED"] = True
    app_config["CDS_GROUPS_ALLOW_CREATE_COMMUNITIES"] = [
        "group-allowed-create-communities"
    ]
    app_config["WEBPACKEXT_MANIFEST_LOADER"] = MockManifestLoader

    app_config["JSONSCHEMAS_HOST"] = "localhost"
    app_config["BABEL_DEFAULT_LOCALE"] = "en"
    app_config["I18N_LANGUAGES"] = [("da", "Danish")]
    app_config["RECORDS_REFRESOLVER_CLS"] = (
        "invenio_records.resolver.InvenioRefResolver"
    )
    app_config["RECORDS_REFRESOLVER_STORE"] = (
        "invenio_jsonschemas.proxies.current_refresolver_store"
    )
    app_config["VOCABULARIES_NAMES_SCHEMES"] = {
        **DEFAULT_VOCABULARIES_NAMES_SCHEMES,
        "cern": {"label": "CERN", "validator": is_legacy_cds, "datacite": "CERN"},
        "inspire": {
            "label": "Inspire",
            "validator": is_inspire_author,
            "datacite": "Inspire",
        },
    }
    app_config["CELERY_TASK_ALWAYS_EAGER"] = True
    app_config["CELERY_CACHE_BACKEND"] = "memory"
    app_config["CELERY_TASK_EAGER_PROPAGATES"] = True
    app_config["CELERY_RESULT_BACKEND"] = "cache"
    app_config["REST_CSRF_ENABLED"] = False  # Disable CSRF globally for tests
    app_config["RDM_RECORDS_IDENTIFIERS_SCHEMES"] = {
        **RDM_RECORDS_IDENTIFIERS_SCHEMES,
        **{
            "inspire": {
                "label": _("Inspire"),
                "validator": is_inspire,
                "datacite": "INSPIRE",
            },
            "lcds": {
                "label": _("CDS Reference"),
                "validator": always_valid,
                "datacite": "CDS",
            },
        },
    }
    return app_config


# @pytest.fixture(scope="module")
# def create_app():
#     """Create test app."""
#     return create_api


@pytest.fixture(scope="function")
def db_session_options():
    """Database session options."""
    # TODO: Look into having this be the default in ``pytest-invenio``
    # This helps with ``sqlalchemy.orm.exc.DetachedInstanceError`` when models are not
    # bound to the session between transactions/requests/service-calls.
    return {"expire_on_commit": False}


@pytest.fixture(scope="module")
def create_app(instance_path):
    """Application factory fixture."""
    return app_factory.create_app


RunningApp = namedtuple(
    "RunningApp",
    [
        "app",
        "superuser_identity",
        "location",
        "cache",
        "resource_type_v",
        "title_type_v",
        "accelerators_type_v",
        "experiments_type_v",
        "languages_type",
        "funders_v",
        "awards_v",
        "licenses_v",
        "contributors_role_v",
        "description_type_v",
        "relation_type_v",
        "subjects_v",
        "initialise_custom_fields",
    ],
)


@pytest.fixture
def running_app(
    app,
    superuser_identity,
    location,
    cache,
    resource_type_v,
    title_type_v,
    accelerators_type_v,
    experiments_type_v,
    languages_v,
    funders_v,
    awards_v,
    licenses_v,
    contributors_role_v,
    description_type_v,
    relation_type_v,
    subjects_v,
    initialise_custom_fields,
):
    """This fixture provides an app with the typically needed db data loaded.

    All of these fixtures are often needed together, so collecting them
    under a semantic umbrella makes sense.
    """
    return RunningApp(
        app,
        superuser_identity,
        location,
        cache,
        resource_type_v,
        title_type_v,
        accelerators_type_v,
        experiments_type_v,
        languages_v,
        funders_v,
        awards_v,
        licenses_v,
        contributors_role_v,
        description_type_v,
        relation_type_v,
        subjects_v,
        initialise_custom_fields,
    )


@pytest.fixture
def test_app(running_app):
    """Get current app."""
    return running_app.app


@pytest.fixture(scope="session")
def headers():
    """Default headers for making requests."""
    return {
        "content-type": "application/json",
        "accept": "application/json",
    }


@pytest.fixture()
def superuser_role_need(db):
    """Store 1 role with 'superuser-access' ActionNeed.

    WHY: This is needed because expansion of ActionNeed is
         done on the basis of a User/Role being associated with that Need.
         If no User/Role is associated with that Need (in the DB), the
         permission is expanded to an empty list.
    """
    role = Role(name="superuser-access")
    db.session.add(role)

    action_role = ActionRoles.create(action=superuser_access, role=role)
    db.session.add(action_role)
    db.session.commit()

    return action_role.need


@pytest.fixture()
def superuser(UserFixture, app, db, superuser_role_need):
    """Superuser."""
    u = UserFixture(
        email="superuser@inveniosoftware.org",
        password="superuser",
    )
    u.create(app, db)

    datastore = app.extensions["security"].datastore
    _, role = datastore._prepare_role_modify_args(u.user, "superuser-access")

    datastore.add_role_to_user(u.user, role)
    db.session.commit()
    return u


@pytest.fixture()
def admin_role_need(db):
    """Store 1 role with 'superuser-access' ActionNeed.

    WHY: This is needed because expansion of ActionNeed is
         done on the basis of a User/Role being associated with that Need.
         If no User/Role is associated with that Need (in the DB), the
         permission is expanded to an empty list.
    """
    role = Role(name="administration-access")
    db.session.add(role)

    action_role = ActionRoles.create(action=administration_access_action, role=role)
    db.session.add(action_role)
    db.session.commit()

    return action_role.need


@pytest.fixture()
def admin(UserFixture, app, db, admin_role_need):
    """Admin user for requests."""
    u = UserFixture(
        email="admin@inveniosoftware.org",
        password="admin",
    )
    u.create(app, db)

    datastore = app.extensions["security"].datastore
    _, role = datastore._prepare_role_modify_args(u.user, "administration-access")

    datastore.add_role_to_user(u.user, role)
    db.session.commit()
    return u


@pytest.fixture()
def administration_role_need(db):
    """Store 1 role with 'administration' ActionNeed.

    WHY: This is needed because expansion of ActionNeed is
         done on the basis of a User/Role being associated with that Need.
         If no User/Role is associated with that Need (in the DB), the
         permission is expanded to an empty list.
    """
    role = Role(name="administration")
    db.session.add(role)

    action_role = ActionRoles.create(action=administration_access_action, role=role)
    db.session.add(action_role)
    db.session.commit()

    return action_role.need


@pytest.fixture()
def administrator(UserFixture, app, db, administration_role_need):
    """Administration user."""
    u = UserFixture(
        email="administrator@inveniosoftware.org",
        password="admin",
    )
    u.create(app, db)

    datastore = app.extensions["security"].datastore
    _, role = datastore._prepare_role_modify_args(u.user, "administration")

    datastore.add_role_to_user(u.user, role)
    db.session.commit()
    return u


@pytest.fixture()
def superuser_identity(admin, superuser_role_need):
    """Superuser identity fixture."""
    identity = admin.identity
    identity.provides.add(superuser_role_need)
    return identity


@pytest.fixture()
def uploader(UserFixture, app, db, test_app):
    """Uploader."""
    u = UserFixture(
        email="uploader@inveniosoftware.org",
        password="uploader",
        preferences={
            "visibility": "public",
            "email_visibility": "restricted",
            "notifications": {
                "enabled": True,
            },
        },
        active=True,
        confirmed=True,
    )
    u.create(app, db)
    UserAggregate.index.refresh()

    return u


@pytest.fixture()
def archiver(UserFixture, app, db):
    """Uploader."""
    ds = app.extensions["invenio-accounts"].datastore
    user = UserFixture(
        email="archiver@inveniosoftware.org",
        password="archiver",
        preferences={
            "visibility": "public",
            "email_visibility": "restricted",
            "notifications": {
                "enabled": True,
            },
        },
        active=True,
        confirmed=True,
    )
    user_obj = user.create(app, db)
    r = ds.create_role(name="oais-archiver", description="1234")
    ds.add_role_to_user(user.user, r)

    return user


@pytest.fixture(scope="module")
def resource_type_type(app):
    """Resource type vocabulary type."""
    return vocabulary_service.create_type(system_identity, "resourcetypes", "rsrct")


@pytest.fixture(scope="module")
def subjects_type(app):
    """Subjects vocabulary type."""
    return vocabulary_service.create_type(system_identity, "subjects", "subj")


@pytest.fixture(scope="module")
def subjects_v(app, subjects_type):
    """Subjects vocabulary records."""
    vocabulary_service.create(
        system_identity,
        {
            "id": "existing-cern-subject",
            "title": {"en": "Existing CERN subject"},
            "type": "subjects",
        },
    )

    vocabulary_service.create(
        system_identity,
        {
            "id": "existing-cds-subject",
            "title": {"en": "Existing CDS subject"},
            "type": "subjects",
        },
    )

    Vocabulary.index.refresh()

    return


@pytest.fixture(scope="module")
def title_type(app):
    """title vocabulary type."""
    return vocabulary_service.create_type(system_identity, "titletypes", "ttyp")


@pytest.fixture(scope="module")
def title_type_v(app, title_type):
    """Title Type vocabulary record."""
    vocabulary_service.create(
        system_identity,
        {
            "id": "subtitle",
            "props": {"datacite": "Subtitle"},
            "title": {"en": "Subtitle"},
            "type": "titletypes",
        },
    )

    vocab = vocabulary_service.create(
        system_identity,
        {
            "id": "alternative-title",
            "props": {"datacite": "AlternativeTitle"},
            "title": {"en": "Alternative title"},
            "type": "titletypes",
        },
    )

    vocab = vocabulary_service.create(
        system_identity,
        {
            "id": "translated-title",
            "props": {"datacite": "TranslatedTitle"},
            "title": {"en": "Translated title"},
            "type": "titletypes",
        },
    )

    Vocabulary.index.refresh()

    return vocab


@pytest.fixture(scope="module")
def accelerators_type(app):
    """accelerators vocabulary type."""
    return vocabulary_service.create_type(system_identity, "accelerators", "acctyp")


@pytest.fixture(scope="module")
def accelerators_type_v(app, accelerators_type):
    """Accelerators Type vocabulary record."""
    vocabulary_service.create(
        system_identity,
        {
            "id": "CERN LEP",
            "title": {"en": "CERN LEP"},
            "type": "accelerators",
        },
    )

    vocab = vocabulary_service.create(
        system_identity,
        {
            "id": "CERN LHC",
            "title": {"en": "CERN LHC"},
            "type": "accelerators",
        },
    )

    vocabulary_service.create(
        system_identity,
        {
            "id": "CERN SPS",
            "title": {"en": "CERN SPS"},
            "type": "accelerators",
        },
    )

    Vocabulary.index.refresh()

    return vocab


@pytest.fixture(scope="module")
def experiments_type(app):
    """experiments vocabulary type."""
    return vocabulary_service.create_type(system_identity, "experiments", "exptyp")


@pytest.fixture(scope="module")
def experiments_type_v(app, experiments_type):
    """Experiments Type vocabulary record."""
    vocabulary_service.create(
        system_identity,
        {
            "id": "ALICE",
            "title": {"en": "ALICE"},
            "description": {"en": '"ALICE - A Large Ion Collider Experiment"'},
            "props": {"link": "http://alice-collaboration.web.cern.ch/"},
            "type": "experiments",
        },
    )

    vocab = vocabulary_service.create(
        system_identity,
        {
            "id": "ATLAS",
            "title": {"en": "ATLAS"},
            "description": {"en": '"ATLAS"'},
            "type": "experiments",
        },
    )
    vocabulary_service.create(
        system_identity,
        {
            "id": "CERN-LHC-ALICE",
            "title": {"en": "CERN LHC ALICE"},
            "type": "experiments",
        },
    )

    vocabulary_service.create(
        system_identity,
        {
            "id": "CERN-LHC-CMS",
            "title": {"en": "CERN LHC CMS"},
            "type": "experiments",
        },
    )
    vocabulary_service.create(
        system_identity,
        {
            "id": "CERN-LEP-ALEPH",
            "title": {"en": "CERN LEP ALEPH"},
            "type": "experiments",
        },
    )
    vocabulary_service.create(
        system_identity,
        {
            "id": "CERN-LHC-LHCb",
            "title": {"en": "CERN LHC LHCb"},
            "type": "experiments",
        },
    )
    vocabulary_service.create(
        system_identity,
        {
            "id": "CERN-NA-062",
            "title": {"en": "CERN NA 062"},
            "type": "experiments",
        },
    )
    vocabulary_service.create(
        system_identity,
        {
            "id": "AMS",
            "title": {"en": "AMS"},
            "type": "experiments",
        },
    )

    Vocabulary.index.refresh()

    return vocab


@pytest.fixture(scope="module")
def resource_type_v(app, resource_type_type):
    """Resource type vocabulary record."""
    vocabulary_service.create(
        system_identity,
        {
            "id": "dataset",
            "icon": "table",
            "props": {
                "csl": "dataset",
                "datacite_general": "Dataset",
                "datacite_type": "",
                "openaire_resourceType": "21",
                "openaire_type": "dataset",
                "eurepo": "info:eu-repo/semantics/other",
                "schema.org": "https://schema.org/Dataset",
                "subtype": "",
                "type": "dataset",
            },
            "title": {"en": "Dataset"},
            "tags": ["depositable", "linkable"],
            "type": "resourcetypes",
        },
    )

    vocabulary_service.create(
        system_identity,
        {  # create base resource type
            "id": "image",
            "props": {
                "csl": "figure",
                "datacite_general": "Image",
                "datacite_type": "",
                "openaire_resourceType": "25",
                "openaire_type": "dataset",
                "eurepo": "info:eu-repo/semantic/other",
                "schema.org": "https://schema.org/ImageObject",
                "subtype": "",
                "type": "image",
            },
            "icon": "chart bar outline",
            "title": {"en": "Image"},
            "tags": ["depositable", "linkable"],
            "type": "resourcetypes",
        },
    )

    vocabulary_service.create(
        system_identity,
        {
            "id": "publication-book",
            "icon": "file alternate",
            "props": {
                "csl": "book",
                "datacite_general": "Text",
                "datacite_type": "Book",
                "openaire_resourceType": "2",
                "openaire_type": "publication",
                "eurepo": "info:eu-repo/semantics/book",
                "schema.org": "https://schema.org/Book",
                "subtype": "publication-book",
                "type": "publication",
            },
            "title": {"en": "Book", "de": "Buch"},
            "tags": ["depositable", "linkable"],
            "type": "resourcetypes",
        },
    )

    vocabulary_service.create(
        system_identity,
        {
            "id": "publication-thesis",
            "icon": "file alternate",
            "props": {
                "csl": "thesis",
                "datacite_general": "Text",
                "datacite_type": "Book",
                "openaire_resourceType": "0006",
                "openaire_type": "publication",
                "eurepo": "info:eu-repo/semantics/doctoralThesis",
                "schema.org": "https://schema.org/Thesis",
                "subtype": "publication-thesis",
                "type": "publication",
            },
            "title": {"en": "Thesis", "de": "Abschlussarbeit"},
            "tags": ["depositable", "linkable"],
            "type": "resourcetypes",
        },
    )

    vocabulary_service.create(
        system_identity,
        {
            "id": "presentation",
            "icon": "group",
            "props": {
                "csl": "speech",
                "datacite_general": "Text",
                "datacite_type": "Presentation",
                "openaire_resourceType": "0004",
                "openaire_type": "publication",
                "eurepo": "info:eu-repo/semantics/lecture",
                "schema.org": "https://schema.org/PresentationDigitalDocument",
                "subtype": "",
                "type": "presentation",
            },
            "title": {"en": "Presentation", "de": "Präsentation"},
            "tags": ["depositable", "linkable"],
            "type": "resourcetypes",
        },
    )

    vocabulary_service.create(
        system_identity,
        {
            "id": "publication",
            "icon": "file alternate",
            "props": {
                "csl": "report",
                "datacite_general": "Text",
                "datacite_type": "",
                "openaire_resourceType": "0017",
                "openaire_type": "publication",
                "eurepo": "info:eu-repo/semantics/other",
                "schema.org": "https://schema.org/CreativeWork",
                "subtype": "",
                "type": "publication",
            },
            "title": {"en": "Publication", "de": "Publikation"},
            "tags": ["depositable", "linkable"],
            "type": "resourcetypes",
        },
    )

    vocabulary_service.create(
        system_identity,
        {
            "id": "image-photo",
            "tags": ["depositable", "linkable"],
            "type": "resourcetypes",
            "title": {"en": "Image: Photo"},
            "props": {
                "csl": "graphic",
                "datacite_general": "Image",
                "datacite_type": "Photo",
                "openaire_resourceType": "0025",
                "openaire_type": "dataset",
                "eurepo": "info:eu-repo/semantics/other",
                "schema.org": "https://schema.org/Photograph",
                "subtype": "image-photo",
                "type": "image",
            },
        },
    )

    vocabulary_service.create(
        system_identity,
        {
            "id": "software",
            "icon": "code",
            "type": "resourcetypes",
            "props": {
                "csl": "software",
                "datacite_general": "Software",
                "datacite_type": "",
                "openaire_resourceType": "0029",
                "openaire_type": "software",
                "eurepo": "info:eu-repo/semantics/other",
                "schema.org": "https://schema.org/SoftwareSourceCode",
                "subtype": "",
                "type": "software",
            },
            "title": {"en": "Software", "de": "Software"},
            "tags": ["depositable", "linkable"],
        },
    )

    vocab = vocabulary_service.create(
        system_identity,
        {
            "id": "other",
            "icon": "asterisk",
            "type": "resourcetypes",
            "props": {
                "csl": "article",
                "datacite_general": "Other",
                "datacite_type": "",
                "openaire_resourceType": "0020",
                "openaire_type": "other",
                "eurepo": "info:eu-repo/semantics/other",
                "schema.org": "https://schema.org/CreativeWork",
                "subtype": "",
                "type": "other",
            },
            "title": {
                "en": "Other",
                "de": "Sonstige",
            },
            "tags": ["depositable", "linkable"],
        },
    )

    Vocabulary.index.refresh()

    return vocab


@pytest.fixture(scope="module")
def languages_type(app):
    """Lanuage vocabulary type."""
    return vocabulary_service.create_type(system_identity, "languages", "lng")


@pytest.fixture(scope="module")
def languages_v(app, languages_type):
    """Language vocabulary record."""
    vocabulary_service.create(
        system_identity,
        {
            "id": "dan",
            "title": {
                "en": "Danish",
                "da": "Dansk",
            },
            "props": {"alpha_2": "da"},
            "tags": ["individual", "living"],
            "type": "languages",
        },
    )

    vocabulary_service.create(
        system_identity,
        {
            "id": "eng",
            "title": {
                "en": "English",
                "da": "Engelsk",
            },
            "tags": ["individual", "living"],
            "type": "languages",
        },
    )

    vocabulary_service.create(
        system_identity,
        {
            "id": "por",
            "title": {
                "en": "Portuguese",
            },
            "tags": ["individual", "living"],
            "type": "languages",
        },
    )

    vocab = vocabulary_service.create(
        system_identity,
        {
            "id": "spa",
            "title": {
                "en": "Spanish",
            },
            "tags": ["individual", "living"],
            "type": "languages",
        },
    )

    Vocabulary.index.refresh()

    return vocab


@pytest.fixture(scope="module")
def funders_v(app, funder_data):
    """Funder vocabulary record."""
    funders_service = current_service_registry.get("funders")
    funder = funders_service.create(
        system_identity,
        funder_data,
    )

    Funder.index.refresh()

    return funder


@pytest.fixture(scope="module")
def awards_v(app, funders_v):
    """Funder vocabulary record."""
    awards_service = current_service_registry.get("awards")
    award = awards_service.create(
        system_identity,
        {
            "id": "00rbzpz17::755021",
            "identifiers": [
                {
                    "identifier": "https://cordis.europa.eu/project/id/755021",
                    "scheme": "url",
                }
            ],
            "number": "755021",
            "title": {
                "en": (
                    "Personalised Treatment For Cystic Fibrosis Patients With "
                    "Ultra-rare CFTR Mutations (and beyond)"
                ),
            },
            "funder": {"id": "00rbzpz17"},
            "acronym": "HIT-CF",
            "program": "H2020",
        },
    )

    Award.index.refresh()

    return award


@pytest.fixture(scope="module")
def licenses(app):
    """Licenses vocabulary type."""
    return vocabulary_service.create_type(system_identity, "licenses", "lic")


@pytest.fixture(scope="module")
def licenses_v(app, licenses):
    """Licenses vocabulary record."""
    cc_zero = vocabulary_service.create(
        system_identity,
        {
            "id": "cc0-1.0",
            "title": {
                "en": "Creative Commons Zero v1.0 Universal",
            },
            "description": {
                "en": (
                    "CC0 waives copyright interest in a work you've created and "
                    "dedicates it to the world-wide public domain. Use CC0 to opt out "
                    "of copyright entirely and ensure your work has the widest reach."
                ),
            },
            "icon": "cc-cc0-icon",
            "tags": ["recommended", "all", "data", "software"],
            "props": {
                "url": "https://creativecommons.org/publicdomain/zero/1.0/legalcode",
                "scheme": "spdx",
                "osi_approved": "",
            },
            "type": "licenses",
        },
    )
    cc_by = vocabulary_service.create(
        system_identity,
        {
            "id": "cc-by-4.0",
            "title": {
                "en": "Creative Commons Attribution 4.0 International",
            },
            "description": {
                "en": (
                    "The Creative Commons Attribution license allows re-distribution "
                    "and re-use of a licensed work on the condition that the creator "
                    "is appropriately credited."
                ),
            },
            "icon": "cc-by-icon",
            "tags": ["recommended", "all", "data"],
            "props": {
                "url": "https://creativecommons.org/licenses/by/4.0/legalcode",
                "scheme": "spdx",
                "osi_approved": "",
            },
            "type": "licenses",
        },
    )

    Vocabulary.index.refresh()

    return [cc_zero, cc_by]


@pytest.fixture(scope="module")
def contributors_role_type(app):
    """Contributor role vocabulary type."""
    return vocabulary_service.create_type(system_identity, "contributorsroles", "cor")


@pytest.fixture(scope="module")
def contributors_role_v(app, contributors_role_type):
    """Contributor role vocabulary record."""
    vocabulary_service.create(
        system_identity,
        {
            "id": "other",
            "props": {"datacite": "Other"},
            "title": {"en": "Other"},
            "type": "contributorsroles",
        },
    )

    vocab = vocabulary_service.create(
        system_identity,
        {
            "id": "datacurator",
            "props": {"datacite": "DataCurator"},
            "title": {"en": "Data curator", "de": "DatenkuratorIn"},
            "type": "contributorsroles",
        },
    )

    vocabulary_service.create(
        system_identity,
        {
            "id": "supervisor",
            "props": {"datacite": "Supervisor"},
            "title": {"en": "Supervisor"},
            "type": "contributorsroles",
        },
    )

    Vocabulary.index.refresh()

    return vocab


@pytest.fixture(scope="module")
def description_type(app):
    """Title vocabulary type."""
    return vocabulary_service.create_type(system_identity, "descriptiontypes", "dty")


@pytest.fixture(scope="module")
def description_type_v(app, description_type):
    """Title Type vocabulary record."""
    vocabulary_service.create(
        system_identity,
        {
            "id": "methods",
            "title": {"en": "Methods"},
            "props": {"datacite": "Methods"},
            "type": "descriptiontypes",
        },
    )
    vocab = vocabulary_service.create(
        system_identity,
        {
            "id": "other",
            "title": {"en": "Other"},
            "props": {"datacite": "Other"},
            "type": "descriptiontypes",
        },
    )
    vocab = vocabulary_service.create(
        system_identity,
        {
            "id": "abstract",
            "title": {"en": "Abstract"},
            "props": {"datacite": "abstract"},
            "type": "descriptiontypes",
        },
    )
    vocab = vocabulary_service.create(
        system_identity,
        {
            "id": "notes",
            "title": {"en": "Notes"},
            "props": {"datacite": "Notes"},
            "type": "descriptiontypes",
        },
    )

    Vocabulary.index.refresh()

    return vocab


@pytest.fixture(scope="module")
def relation_type(app):
    """Relation type vocabulary type."""
    return vocabulary_service.create_type(system_identity, "relationtypes", "rlt")


@pytest.fixture(scope="module")
def relation_type_v(app, relation_type):
    """Relation type vocabulary record."""
    vocabulary_service.create(
        system_identity,
        {
            "id": "iscitedby",
            "props": {"datacite": "IsCitedBy"},
            "title": {"en": "Is cited by"},
            "type": "relationtypes",
        },
    )

    vocab = vocabulary_service.create(
        system_identity,
        {
            "id": "cites",
            "props": {"datacite": "Cites"},
            "title": {"en": "Cites", "de": "Zitiert"},
            "type": "relationtypes",
        },
    )

    Vocabulary.index.refresh()

    return vocab


@pytest.fixture(scope="function")
def initialise_custom_fields(app, db, location, cli_runner):
    """Fixture initialises custom fields."""
    return cli_runner(create_records_custom_field)


@pytest.fixture(scope="module")
def funder_data():
    """Implements a funder's data."""
    return {
        "id": "00rbzpz17",
        "identifiers": [
            {
                "identifier": "00rbzpz17",
                "scheme": "ror",
            },
            {"identifier": "10.13039/501100001665", "scheme": "doi"},
        ],
        "name": "Agence Nationale de la Recherche",
        "title": {
            "fr": "National Agency for Research",
        },
        "country": "FR",
    }


@pytest.fixture()
def minimal_restricted_record():
    """Minimal record data as dict coming from the external world."""
    return {
        "pids": {},
        "access": {
            "record": "restricted",
            "files": "restricted",
        },
        "files": {
            "enabled": False,  # Most tests don't care about files
        },
        "metadata": {
            "creators": [
                {
                    "person_or_org": {
                        "family_name": "Brown",
                        "given_name": "Troy",
                        "type": "personal",
                    }
                },
            ],
            "publication_date": "2020-06-01",
            "publisher": "Acme Inc",
            "resource_type": {"id": "image-photo"},
            "title": "A Romans story",
        },
    }


@pytest.fixture()
def minimal_record_with_files():
    """Minimal record data as dict coming from the external world."""
    return {
        "pids": {},
        "access": {
            "record": "public",
            "files": "public",
        },
        "files": {
            "enabled": True,
        },
        "metadata": {
            "creators": [
                {
                    "person_or_org": {
                        "family_name": "Brown",
                        "given_name": "Troy",
                        "type": "personal",
                    }
                },
                {
                    "person_or_org": {
                        "name": "Troy Inc.",
                        "type": "organizational",
                    },
                },
            ],
            "publication_date": "2020-06-01",
            # because DATACITE_ENABLED is True, this field is required
            "publisher": "Acme Inc",
            "resource_type": {"id": "image-photo"},
            "title": "Roman files",
        },
    }


@pytest.fixture(scope="function")
def add_pid(db):
    """Fixture to add a row to the pidstore_pid table."""

    def _add_pid(
        pid_type, pid_value, object_uuid, status=PIDStatus.REGISTERED, object_type="rec"
    ):
        pid = PersistentIdentifier.create(
            pid_type=pid_type,
            pid_value=pid_value,
            status=status,
            object_uuid=object_uuid,
            object_type=object_type,
        )
        db.session.commit()
        return pid

    return _add_pid


@pytest.fixture(scope="module")
def legacy_community():
    """A basic community fixture."""
    return {
        "access": {
            "visibility": "public",
            "members_visibility": "public",
            "record_submission_policy": "open",
        },
        "metadata": {
            "title": "Legacy Collection",
        },
        "slug": "legacy-community",
    }


@pytest.fixture(scope="module")
def legacy_restricted_community():
    """A restricted community fixture."""
    return {
        "access": {
            "visibility": "restricted",
            "members_visibility": "restricted",
            "record_submission_policy": "closed",
        },
        "metadata": {
            "title": "Legacy Restricted Collection",
        },
        "slug": "legacy-restricted-community",
    }


@pytest.fixture(scope="function")
def user_1(app):
    """Create a user."""
    profile_1 = {
        "group": "CA",
        "orcid": "0000-0001-8135-3489",
        "mailbox": "92918",
        "section": "IR",
        "full_name": "Joe Doe",
        "person_id": "11111",
        "department": "IT",
        "given_name": "Joe",
        "family_name": "Doe",
        "affiliations": "CERN",
    }

    user_1 = testutils.create_test_user("joe@test.org", id=1, user_profile=profile_1)
    return user_1


@pytest.fixture(scope="function")
def user_2(app):
    """Create a user."""
    profile_2 = {
        "group": "CA",
        "mailbox": "92918",
        "section": "IR",
        "full_name": "Jane Doe",
        "person_id": "11112",
        "department": "IT",
        "given_name": "Jane",
        "family_name": "Doe",
        "affiliations": "CERN",
    }
    user_2 = testutils.create_test_user("jane2@test.org", id=2, user_profile=profile_2)
    return user_2


@pytest.fixture(scope="function")
def user_3(app):
    """Create a user."""
    profile_3 = {
        "group": "CA",
        "mailbox": "92918",
        "orcid": "0009-0007-7638-4652",
        "section": "IR",
        "full_name": "John Doe",
        "person_id": "11113",
        "department": "IT",
        "given_name": "John",
        "family_name": "Doe",
        "affiliations": "CERN",
    }
    user_3 = testutils.create_test_user("john@test.org", id=3, user_profile=profile_3)
    return user_3


@pytest.fixture(scope="function")
def name_user_3():
    """Name data."""
    return {
        "id": "0009-0007-7638-4652",
        "name": "Doe, John",
        "given_name": "John",
        "family_name": "Doe",
        "identifiers": [
            {"identifier": "0009-0007-7638-4652", "scheme": "orcid"},
        ],
        "affiliations": [{"name": "CERN"}],
    }


@pytest.fixture(scope="function")
def name_full_data():
    """Full name data."""
    return {
        "id": "0000-0001-8135-3489",
        "name": "Doe, John",
        "given_name": "John",
        "family_name": "Doe",
        "identifiers": [
            {"identifier": "0000-0001-8135-3489", "scheme": "orcid"},
            {"identifier": "gnd:4079154-3", "scheme": "gnd"},
        ],
        "affiliations": [{"name": "CustomORG"}],
    }
