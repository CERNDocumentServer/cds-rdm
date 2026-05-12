// This file is part of CDS RDM
// Copyright (C) 2025 CERN.
//
// CDS RDM is free software; you can redistribute it and/or modify it
// under the terms of the GPL-2.0 License; see LICENSE file for more details.

import React, { Component } from "react";
import { Button, Divider, Grid, Header, Icon, Message, Modal } from "semantic-ui-react";
import { i18next } from "@translations/invenio_app_rdm/i18next";
import { EPApprovalSubmitModal } from "./EPApprovalSubmitModal";
import { CreatePublicRecordModal } from "./CreatePublicRecordModal";

export class EPApprovalManageSection extends Component {
  constructor(props) {
    super(props);
    const recordManagementDiv = document.getElementById("recordManagement");
    const epApprovalData = recordManagementDiv
      ? JSON.parse(recordManagementDiv.dataset.epApproval || "null")
      : null;

    this.state = {
      epApproval: epApprovalData,
      submitModalOpen: false,
      createPublicModalOpen: false,
      newVersionModalOpen: false,
      // Prefer backend-provided public_record_id (reliable across all versions).
      publicRecordId: epApprovalData?.public_record_id || null,
    };

    this._newVersionClickHandler = null;
  }

  componentDidMount() {
    this._attachNewVersionInterceptor();
  }

  componentDidUpdate(_prevProps, prevState) {
    const { epApproval } = this.state;
    const prevEpApproval = prevState.epApproval;
    if (epApproval?.open_request?.status !== prevEpApproval?.open_request?.status) {
      this._detachNewVersionInterceptor();
      this._attachNewVersionInterceptor();
    }
  }

  componentWillUnmount() {
    this._detachNewVersionInterceptor();
  }

  _attachNewVersionInterceptor() {
    const { epApproval } = this.state;
    if (epApproval?.open_request?.status !== "submitted") return;

    // Find the "New version" button rendered by InvenioRDM's RecordManagement.
    const btn = Array.from(document.querySelectorAll("button")).find(
      (b) => b.textContent.trim() === i18next.t("New version")
    );
    if (!btn) return;

    this._newVersionClickHandler = (e) => {
      e.stopImmediatePropagation();
      e.preventDefault();
      this.setState({ newVersionModalOpen: true });
    };
    btn.addEventListener("click", this._newVersionClickHandler, true);
    this._newVersionBtn = btn;
  }

  _detachNewVersionInterceptor() {
    if (this._newVersionBtn && this._newVersionClickHandler) {
      this._newVersionBtn.removeEventListener(
        "click",
        this._newVersionClickHandler,
        true
      );
    }
    this._newVersionBtn = null;
    this._newVersionClickHandler = null;
  }

  get shouldRender() {
    const { epApproval } = this.state;
    return (
      epApproval &&
      (epApproval.community_enrolled || epApproval.is_public_approved_record)
    );
  }

  handleSubmitSuccess = (request) => {
    this.setState((prev) => ({
      submitModalOpen: false,
      epApproval: {
        ...prev.epApproval,
        open_request: {
          id: request.id,
          status: "submitted",
          links: request.links,
        },
      },
    }));
  };

  handlePublicRecordCreated = (publicRecord) => {
    this.setState({ publicRecordId: publicRecord.id });
  };

  render() {
    const {
      epApproval,
      submitModalOpen,
      createPublicModalOpen,
      newVersionModalOpen,
      publicRecordId,
    } = this.state;
    const { record } = this.props;

    if (!this.shouldRender) {
      return null;
    }

    // Public EP-approved record — nothing to manage here; sidebar shows the draft link.
    if (epApproval.is_public_approved_record) {
      return null;
    }

    const {
      can_submit,
      can_create_public,
      open_request,
      approved_report_number,
      receiver_group,
    } = epApproval;

    const isPending = open_request?.status === "submitted";
    const isDeclined = open_request?.status === "declined";
    const isAccepted = open_request?.status === "accepted";
    // approved_report_number is always populated by the backend (scans the full
    // parent if the current version doesn't carry the CF itself).
    const canResubmit = can_submit && !isPending && !approved_report_number && !isAccepted;
    // can_create_public comes from the backend and already encodes version-order
    // eligibility (only versions >= the approved version may create a public record).
    const canCreatePublic = can_create_public && !publicRecordId;

    return (
      <Grid.Column className="pb-20 pt-0">
        <Divider horizontal>
          <Header as="h4">{i18next.t("Manage Publication")}</Header>
        </Divider>

        {/* Accepted — show approved report number (linked to the request) + create or view public record */}
        {approved_report_number && (
          <>
            {(() => {
              const requestLink =
                open_request?.links?.self_html ||
                (open_request?.id ? `/requests/${open_request.id}` : null);
              return requestLink ? (
                <p className="mb-5 text-align-center">
                  {i18next.t("Approved as {{rn}}", { rn: approved_report_number })}
                  {" — "}
                  <a href={requestLink}>
                    {i18next.t("See approved request")}
                    <Icon name="external alternate" className="ml-5" />
                  </a>
                </p>
              ) : (
                <p className="mb-5 text-align-center">
                  {i18next.t("Approved as {{rn}}", { rn: approved_report_number })}
                </p>
              );
            })()}
            {!publicRecordId && canCreatePublic && (
              <>
                <Button
                  fluid
                  primary
                  size="medium"
                  icon="world"
                  labelPosition="left"
                  content={i18next.t("Create public approved record")}
                  onClick={() => this.setState({ createPublicModalOpen: true })}
                  className="mb-5"
                />
                <CreatePublicRecordModal
                  open={createPublicModalOpen}
                  record={record}
                  approvedReportNumber={approved_report_number}
                  onClose={() => this.setState({ createPublicModalOpen: false })}
                  onSuccess={this.handlePublicRecordCreated}
                />
              </>
            )}
          </>
        )}

        {/* Pending — link to the open request */}
        {isPending && (
          <Button
            fluid
            size="medium"
            icon
            labelPosition="right"
            href={open_request.links?.self_html}
            as="a"
            className="mb-5 secondary"
          >
            {i18next.t("Document requested for approval")}
            <Icon name="external alternate" />
          </Button>
        )}

        {/* Declined — warning message + link to request + allow re-submission */}
        {isDeclined && (
          <Message warning size="small" className="mb-5">
            <Message.Content>
              {i18next.t("The approval request was declined.")}
              {open_request.links?.self_html && (
                <>
                  {" "}
                  <a
                    href={open_request.links.self_html}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {i18next.t("View request")}
                    <Icon name="external alternate" className="ml-5" />
                  </a>
                </>
              )}
            </Message.Content>
          </Message>
        )}

        {/* Submit / re-submit button */}
        {canResubmit && (
          <>
            <Button
              fluid
              positive
              size="medium"
              onClick={() => this.setState({ submitModalOpen: true })}
              className="mb-5"
            >
              {isDeclined
                ? i18next.t("Request approval again")
                : i18next.t("Request approval of this document")}
            </Button>
            <EPApprovalSubmitModal
              open={submitModalOpen}
              record={record}
              receiverGroup={receiver_group}
              onClose={() => this.setState({ submitModalOpen: false })}
              onSuccess={this.handleSubmitSuccess}
            />
          </>
        )}
      {/* New-version warning modal — shown when user clicks "New version" while a request is pending */}
      <Modal
        open={newVersionModalOpen}
        onClose={() => this.setState({ newVersionModalOpen: false })}
        size="small"
      >
        <Modal.Header>
          <Icon name="warning sign" color="yellow" />
          {i18next.t("EP approval request pending")}
        </Modal.Header>
        <Modal.Content>
          <p>
            {i18next.t(
              "An EP approval request is currently pending for this record. " +
                "Creating a new version is not recommended while the request is open. " +
                "If you need to create a new version, please cancel the approval request first."
            )}
          </p>
        </Modal.Content>
        <Modal.Actions>
          <Button
            primary
            onClick={() => this.setState({ newVersionModalOpen: false })}
          >
            {i18next.t("OK")}
          </Button>
        </Modal.Actions>
      </Modal>
    </Grid.Column>
    );
  }
}
