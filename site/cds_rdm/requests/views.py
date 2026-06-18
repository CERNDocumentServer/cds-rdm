# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2025 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""CDS Committee Approval API views."""

import copy

from flask import Blueprint, current_app, g, jsonify, request
from flask_login import login_required
from invenio_access.permissions import system_identity
from invenio_communities.communities.records.api import Community
from invenio_communities.generators import CommunityRoleNeed
from invenio_db import db
from invenio_pidstore.errors import PIDDoesNotExistError
from invenio_pidstore.models import PersistentIdentifier
from invenio_rdm_records.proxies import (
    current_rdm_records_service,
    current_record_communities_service,
)
from invenio_rdm_records.records.api import RDMRecord
from invenio_records_resources.services.errors import PermissionDeniedError
from invenio_requests.proxies import current_requests_service
from invenio_requests.resolvers.registry import ResolverRegistry

from .committee_approval import CommitteeApprovalRequest


def create_committee_approval_bp(app):
    """Create committee approval API blueprint."""
    bp = Blueprint("cds_committee_approval", __name__)

    @bp.route("/records/<pid_value>/committee-approval", methods=["POST"])
    @login_required
    def submit_committee_approval(pid_value):
        """Submit a committee approval request for a published record."""
        try:
            record = current_rdm_records_service.read(
                g.identity, pid_value, expand=False
            )
        except (PIDDoesNotExistError, PermissionDeniedError) as e:
            return jsonify({"message": str(e)}), 409

        body = request.get_json(force=True) or {}
        receiver_group = body.pop("receiver_group", None)
        payload = body.get("payload", {})

        if not receiver_group:
            return jsonify({"message": "receiver_group is required"}), 400

        try:
            # Resolve receiver group entity.
            receiver = ResolverRegistry.resolve_entity(
                {"group": receiver_group}, raise_=True
            )

            title = record.data.get("metadata", {}).get("title", "")
            req = current_requests_service.create(
                identity=g.identity,
                data={
                    "title": f'Committee approval for "{title}"',
                    "payload": payload,
                },
                request_type=CommitteeApprovalRequest,
                receiver=receiver,
                topic=record._record,
            )
        except PermissionDeniedError:
            return jsonify({"message": "Permission denied"}), 403
        except Exception as e:
            return jsonify({"message": str(e)}), 400

        return jsonify(req.to_dict()), 201

    @bp.route("/records/<pid_value>/committee-approval/publish-public", methods=["POST"])
    @login_required
    def publish_public_record(pid_value):
        """Create a public approved record from an approved draft.

        Requires the calling user to be a community manager/owner of the
        record's enrolled community.

        Steps:
        1. Read the approved draft — must have committee_approval.reportnumber set on parent.
        2. Build a new public record: copy metadata + files, set access=public.
        3. Create draft, import files, write committee_approval to both parents, publish.
        4. Return the new public record id and links.
        """
        # --- read + authorise ---
        try:
            draft_record = current_rdm_records_service.read(
                g.identity, pid_value, expand=False
            )
        except (PIDDoesNotExistError, PermissionDeniedError) as e:
            return jsonify({"message": str(e)}), 403

        # Read committee_approval from the internal draft's parent.
        src_pid_obj = PersistentIdentifier.get("recid", pid_value)
        src_rec_obj = RDMRecord.get_record(src_pid_obj.object_uuid)
        ea = (src_rec_obj.parent.get("permission_flags") or {}).get("committee_approval") or {}
        report_number = ea.get("reportnumber")

        if not report_number:
            return jsonify({"message": "Record has no approved report number."}), 400

        # Check that the calling user is a community manager/owner of the enrolled community.
        default_community_id = (
            draft_record.data.get("parent", {}).get("communities", {}).get("default")
        )
        if not default_community_id:
            return jsonify({"message": "Record has no default community."}), 400

        identity = g.identity
        allowed_roles = ("curator", "manager", "owner")
        if not any(
            CommunityRoleNeed(default_community_id, role) in identity.provides
            for role in allowed_roles
        ):
            return jsonify({"message": "Permission denied"}), 403

        # Reject if the calling version predates the approved version.
        approved_version_recid = ea.get("approved_internal_version")
        if approved_version_recid and approved_version_recid != pid_value:
            try:
                appr_pid = PersistentIdentifier.get("recid", approved_version_recid)
                appr_rec = RDMRecord.get_record(appr_pid.object_uuid)
                cur_pid = PersistentIdentifier.get("recid", pid_value)
                cur_rec = RDMRecord.get_record(cur_pid.object_uuid)
                if cur_rec.versions.index < appr_rec.versions.index:
                    return (
                        jsonify(
                            {
                                "message": (
                                    "Cannot create a public record from a version that "
                                    "predates the approved version."
                                )
                            }
                        ),
                        400,
                    )
            except Exception:
                pass  # fail open — report_number check above already validated

        # Guard: refuse if a public record was already created.
        if ea.get("approved_public_version"):
            return (
                jsonify(
                    {
                        "message": "A public record for this approval already exists.",
                        "id": ea["approved_public_version"],
                    }
                ),
                409,
            )

        # --- build new public record data ---
        src = draft_record.data
        src_id = src["id"]

        # Strip apprn from identifiers — CommitteeApprovalComponent regenerates it
        # from committee_approval.reportnumber on every update_draft / publish.
        new_identifiers = [
            i
            for i in src.get("metadata", {}).get("identifiers", [])
            if i.get("scheme") != "apprn"
        ]

        new_related = list(src.get("metadata", {}).get("related_identifiers", []))
        isversionof_entry = {
            "identifier": src_id,
            "scheme": "cds",
            "relation_type": {"id": "isversionof"},
        }
        src_resource_type = src.get("metadata", {}).get("resource_type")
        if src_resource_type:
            isversionof_entry["resource_type"] = src_resource_type
        new_related.append(isversionof_entry)

        new_metadata = {
            **copy.deepcopy(src.get("metadata", {})),
            "identifiers": new_identifiers,
            "related_identifiers": new_related,
        }

        new_record_data = {
            "metadata": new_metadata,
            "custom_fields": src.get("custom_fields", {}),
            "access": {"record": "public", "files": "public"},
            "files": {"enabled": src.get("files", {}).get("enabled", False)},
        }

        try:
            # Create draft as the calling user so they own the public record.
            new_draft = current_rdm_records_service.create(g.identity, new_record_data)
            community_obj = Community.get_record(default_community_id)
            new_draft._record.parent.communities.add(community_obj, default=True)
            new_draft._record.parent.commit()

            if src.get("files", {}).get("enabled", False):
                new_draft._record.files.copy(src_rec_obj.files)
                new_draft._record.commit()

            # Write committee_approval into the public record's permission_flags.
            # source_internal_version marks this as the public copy and links back.
            pf = new_draft._record.parent.get("permission_flags") or {}
            pf["committee_approval"] = {
                "reportnumber": report_number,
                "source_internal_version": src_id,
            }
            new_draft._record.parent["permission_flags"] = pf
            new_draft._record.parent.commit()
            db.session.commit()

            # update_draft triggers CommitteeApprovalComponent which regenerates
            # the apprn identifier (now reads from parent committee_approval).
            new_record = current_rdm_records_service.publish(
                system_identity, new_draft.id
            )
        except Exception as e:
            return jsonify({"message": str(e)}), 400

        # Submit an inclusion request to the CERN Research community.
        cern_scientific_community_id = current_app.config.get(
            "CDS_CERN_SCIENTIFIC_COMMUNITY_ID"
        )
        if cern_scientific_community_id:
            try:
                current_record_communities_service.add(
                    system_identity,
                    new_record.data["id"],
                    data={
                        "communities": [
                            {
                                "id": cern_scientific_community_id,
                                "require_review": True,
                                "comment": {
                                    "payload": {
                                        "content": (
                                            f"This inclusion request was automatically "
                                            f"generated when publishing the EP-approved "
                                            f"public record for {report_number}. The "
                                            f"document has been reviewed and approved by "
                                            f"the EP Publication Committee."
                                        )
                                    }
                                },
                            }
                        ]
                    },
                )
            except Exception as e:
                current_app.logger.warning(
                    f"Could not submit CERN Research inclusion request for "
                    f"{new_record.data['id']}: {e}"
                )

        new_record_id = new_record.data["id"]

        # Write approved_public_version to the internal draft's parent so
        # future page loads know a public record was created.
        back_link_warning = None
        try:
            pf = src_rec_obj.parent.get("permission_flags") or {}
            pf["committee_approval"] = {
                **ea,
                "approved_public_version": new_record_id,
            }
            src_rec_obj.parent["permission_flags"] = pf
            src_rec_obj.parent.commit()
            db.session.commit()

            # Also add the isvariantformof back-link to the source version.
            back_draft = current_rdm_records_service.edit(system_identity, id_=src_id)
            back_data = back_draft.data
            back_related = list(
                back_data.get("metadata", {}).get("related_identifiers", [])
            )
            already_linked = any(
                r.get("scheme") == "cds"
                and (r.get("relation_type") or {}).get("id") == "isvariantformof"
                and r.get("identifier") == new_record_id
                for r in back_related
            )
            if not already_linked:
                isvariantformof_entry = {
                    "identifier": new_record_id,
                    "scheme": "cds",
                    "relation_type": {"id": "isvariantformof"},
                }
                pub_resource_type = new_record.data.get("metadata", {}).get(
                    "resource_type"
                )
                if pub_resource_type:
                    isvariantformof_entry["resource_type"] = pub_resource_type
                back_related.append(isvariantformof_entry)
                back_data["metadata"]["related_identifiers"] = back_related
                current_rdm_records_service.update_draft(
                    system_identity, id_=back_draft.id, data=back_data
                )
                current_rdm_records_service.publish(system_identity, id_=back_draft.id)
        except Exception:
            back_link_warning = (
                "Public record created but back-link on source version failed."
            )

        response_body = {"id": new_record_id, "links": new_record.data.get("links", {})}
        if back_link_warning:
            response_body["warning"] = back_link_warning
        return jsonify(response_body), 201

    return bp
