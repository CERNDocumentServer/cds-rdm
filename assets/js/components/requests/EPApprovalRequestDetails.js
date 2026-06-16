// This file is part of CDS RDM
// Copyright (C) 2025 CERN.
//
// CDS RDM is free software; you can redistribute it and/or modify it
// under the terms of the GPL-2.0 License; see LICENSE file for more details.

import React from "react";
import PropTypes from "prop-types";
import { Grid, Table } from "semantic-ui-react";
import { i18next } from "@translations/invenio_app_rdm/i18next";
import { Timeline } from "@js/invenio_requests/timelineParent";
import RequestMetadata from "@js/invenio_requests/request/RequestMetadata";

const BoolCell = ({ value }) => (
  <>{value ? i18next.t("Yes") : i18next.t("No")}</>
);

BoolCell.propTypes = { value: PropTypes.bool.isRequired };

const EPApprovalPayloadCard = ({ request }) => {
  const payload = request.payload || {};
  const topicLinks = request.topic?.links || {};

  return (
    <Table definition celled compact className="mb-15">
      <Table.Body>
        {topicLinks.self_html && (
          <Table.Row>
            <Table.Cell>{i18next.t("Record")}</Table.Cell>
            <Table.Cell>
              <a href={topicLinks.self_html} target="_blank" rel="noreferrer">
                {topicLinks.self_html}
              </a>
            </Table.Cell>
          </Table.Row>
        )}
        <Table.Row>
          <Table.Cell>{i18next.t("Experiment")}</Table.Cell>
          <Table.Cell>{payload.experiment || "—"}</Table.Cell>
        </Table.Row>
        <Table.Row>
          <Table.Cell>{i18next.t("Submitted by")}</Table.Cell>
          <Table.Cell>{payload.submitted_by || "—"}</Table.Cell>
        </Table.Row>
        <Table.Row>
          <Table.Cell>{i18next.t("Role")}</Table.Cell>
          <Table.Cell>{payload.role || "—"}</Table.Cell>
        </Table.Row>
        {payload.latest_version_url && (
          <Table.Row>
            <Table.Cell>{i18next.t("Latest version at")}</Table.Cell>
            <Table.Cell>
              <a
                href={payload.latest_version_url}
                target="_blank"
                rel="noreferrer"
              >
                {payload.latest_version_url}
              </a>
            </Table.Cell>
          </Table.Row>
        )}
        <Table.Row>
          <Table.Cell>{i18next.t("Rapid approval")}</Table.Cell>
          <Table.Cell>
            <BoolCell value={!!payload.rapid_approval} />
          </Table.Cell>
        </Table.Row>
        <Table.Row>
          <Table.Cell>{i18next.t("CB review completed")}</Table.Cell>
          <Table.Cell>
            <BoolCell value={!!payload.cb_review_completed} />
            {payload.cb_review_completed && payload.cb_process_type && (
              <> ({payload.cb_process_type})</>
            )}
          </Table.Cell>
        </Table.Row>
        <Table.Row>
          <Table.Cell>{i18next.t("Paper signed by whole collaboration")}</Table.Cell>
          <Table.Cell>
            <BoolCell value={!!payload.paper_signed} />
            {!payload.paper_signed && payload.num_non_signers > 0 && (
              <> — {i18next.t("{{n}} non-signer(s)", { n: payload.num_non_signers })}</>
            )}
          </Table.Cell>
        </Table.Row>
        {payload.controversy && (
          <Table.Row>
            <Table.Cell>{i18next.t("Controversy")}</Table.Cell>
            <Table.Cell>{i18next.t("Yes")}</Table.Cell>
          </Table.Row>
        )}
        {payload.additional_communication && (
          <Table.Row>
            <Table.Cell>{i18next.t("Additional communication")}</Table.Cell>
            <Table.Cell style={{ whiteSpace: "pre-wrap" }}>
              {payload.additional_communication}
            </Table.Cell>
          </Table.Row>
        )}
        {payload.approved_report_number && (
          <Table.Row positive>
            <Table.Cell>{i18next.t("Approved report number")}</Table.Cell>
            <Table.Cell>
              <strong>{payload.approved_report_number}</strong>
            </Table.Cell>
          </Table.Row>
        )}
      </Table.Body>
    </Table>
  );
};

EPApprovalPayloadCard.propTypes = {
  request: PropTypes.object.isRequired,
};

export const EPApprovalAwareRequestDetails = ({
  request,
  userAvatar,
  permissions,
  config,
}) => {
  const isEPApproval = request.type === "ep-approval";

  return (
    <Grid stackable reversed="mobile">
      <Grid.Column mobile={16} tablet={12} computer={13}>
        {isEPApproval && <EPApprovalPayloadCard request={request} />}
        <Timeline
          userAvatar={userAvatar}
          request={request}
          permissions={permissions}
        />
      </Grid.Column>
      <Grid.Column mobile={16} tablet={4} computer={3}>
        <RequestMetadata
          request={request}
          permissions={permissions}
          config={config}
        />
      </Grid.Column>
    </Grid>
  );
};

EPApprovalAwareRequestDetails.propTypes = {
  request: PropTypes.object.isRequired,
  userAvatar: PropTypes.string,
  permissions: PropTypes.object.isRequired,
  config: PropTypes.object.isRequired,
};

EPApprovalAwareRequestDetails.defaultProps = {
  userAvatar: "",
};
