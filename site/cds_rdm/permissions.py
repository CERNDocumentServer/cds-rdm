"""Permission policy."""
from invenio_communities.permissions import CommunityPermissionPolicy
from invenio_records_permissions.generators import SystemProcess


class CDSCommunitiesPermissionPolicy(CommunityPermissionPolicy):
    """Communities permission policy of CDS."""

    # for now, we want to restrict the creation of communities to admins
    can_create = [SystemProcess()]
