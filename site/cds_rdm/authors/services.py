from invenio_records_permissions.generators import Disable, SystemProcess
from invenio_records_permissions.policies import BasePermissionPolicy
from invenio_records_resources.services.base import Service
from invenio_records_resources.services.base.config import ServiceConfig
from invenio_records_resources.services.records.components import DataComponent
from invenio_records_resources.services.records.schema import ServiceSchemaWrapper
from invenio_records_resources.services.uow import RecordCommitOp, unit_of_work

from .api import Author
from .schema import AuthorSchema


class AuthorsService(Service):
    """Authors service."""

    @property
    def record_cls(self):
        """Record class."""
        return self.config.record_cls

    @property
    def schema(self):
        """Returns the data schema instance."""
        return ServiceSchemaWrapper(self, schema=self.config.schema)

    def read(self, identity, _id):
        """Read an author."""
        self.require_permission(identity, "read")
        record = self.record_cls.pid.resolve(_id)
        return record

    @unit_of_work()
    def create(self, identity, data, uow=None):
        """Create an author."""
        self.require_permission(identity, "create")

        data, _ = self.schema.load(
            data,
            context={"identity": identity},
        )

        author = self.record_cls.create(data)
        # Run components
        self.run_components("create", identity, data=data, record=author, uow=uow)
        uow.register(RecordCommitOp(author))
        return author

    @unit_of_work()
    def update(self, identity, _id, data, uow=None):
        """Update an author."""
        self.require_permission(identity, "update")
        author = self.record_cls.pid.resolve(_id)
        data, _ = self.schema.load(
            data,
            context={"identity": identity},
        )
        # Run components
        self.run_components("update", identity, data=data, record=author, uow=uow)
        uow.register(RecordCommitOp(author))
        return author


class AuthorPermissionPolicy(BasePermissionPolicy):
    """Access control configuration for authors."""

    can_read = [SystemProcess()]
    can_create = [SystemProcess()]
    can_update = [SystemProcess()]

    # Not supported actions
    can_search = [Disable()]
    can_delete = [Disable()]


class AuthorsServiceConfig(ServiceConfig):
    """Authors service configuration."""

    service_id = "authors"
    permission_policy_cls = AuthorPermissionPolicy
    record_cls = Author
    schema = AuthorSchema

    components = [
        DataComponent,
    ]
