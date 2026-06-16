// This file is part of CDS RDM
// Copyright (C) 2025 CERN.
//
// CDS RDM is free software; you can redistribute it and/or modify it
// under the terms of the GPL-2.0 License; see LICENSE file for more details.

import React, { Component } from "react";
import {
  Button,
  Divider,
  Grid,
  Header,
  Icon,
  Message,
  Modal,
  Step,
} from "semantic-ui-react";
import { i18next } from "@translations/invenio_app_rdm/i18next";
import { EPApprovalSubmitModal } from "./EPApprovalSubmitModal";
import { CreatePublicRecordModal } from "./CreatePublicRecordModal";
import PropTypes from "prop-types";

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
      // Tracks the public record id/url after creation (optimistic UI update).
      // can_create_public from backend already handles the case where one exists.
      publicRecordId: null,
      publicRecordUrl: null,
    };

    this._newVersionClickHandler = null;
  }

  componentDidMount() {
    this._attachNewVersionInterceptor();
  }

  componentDidUpdate(_prevProps, prevState) {
    const { epApproval } = this.state;
    const prevEpApproval = prevState.epApproval;
    if (
      epApproval?.open_request?.status !== prevEpApproval?.open_request?.status
    ) {
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
    this.setState({
      publicRecordId: publicRecord.id,
      publicRecordUrl: publicRecord.links?.self_html || null,
    });
  };

  render() {
    const {
      epApproval,
      submitModalOpen,
      createPublicModalOpen,
      newVersionModalOpen,
      publicRecordId,
      publicRecordUrl,
    } = this.state;
    const { record } = this.props;

    if (!this.shouldRender) {
      return null;
    }

    // Public EP-approved record — show a compact provenance note.
    if (epApproval.is_public_approved_record) {
      const {
        approved_report_number: pubRn,
        draft_record_id,
        can_view_reviewed_version,
      } = epApproval;
      return (
        <Grid.Column className="pb-20 pt-0">
          <Message size="small" positive>
            <Icon name="check circle" />
            {pubRn
              ? i18next.t("EP-approved as {{rn}}", { rn: pubRn })
              : i18next.t("EP-approved record")}
            {can_view_reviewed_version && draft_record_id && (
              <>
                {" · "}
                <a
                  href={`/records/${draft_record_id}`}
                  target="_blank"
                  rel="noreferrer"
                >
                  {i18next.t("Review history")}
                  <Icon name="external alternate" className="ml-5" />
                </a>
              </>
            )}
          </Message>
        </Grid.Column>
      );
    }

    const {
      can_submit,
      can_create_public,
      open_request,
      approved_report_number,
      receiver_group,
      ep_approval,
    } = epApproval;

    // Public record URL: prefer the URL captured at creation time; fall back to
    // the recid stored on the parent (approved_public_version) for page-load case.
    const resolvedPublicRecordUrl =
      publicRecordUrl ||
      (ep_approval?.approved_public_version
        ? `/records/${ep_approval.approved_public_version}`
        : null);

    const isPending = open_request?.status === "submitted";
    const isDeclined = open_request?.status === "declined";
    const isAccepted = open_request?.status === "accepted";
    // approved_report_number is always populated by the backend (scans the full
    // parent if the current version doesn't carry the CF itself).
    const canResubmit =
      can_submit && !isPending && !approved_report_number && !isAccepted;
    // can_create_public comes from the backend and already encodes version-order
    // eligibility (only versions >= the approved version may create a public record).
    const canCreatePublic = can_create_public && !publicRecordId;

    const requestLink =
      open_request?.links?.self_html ||
      (open_request?.id ? `/requests/${open_request.id}` : null);

    // Timeline step states
    // Step 1 — Request for approval
    const step1Completed = !!approved_report_number;
    const step1Active = !step1Completed && !isPending;

    // Step 2 — EP Board review
    const step2Completed = !!approved_report_number;
    const step2Active = isPending;
    const step2Disabled = !isPending && !step2Completed;

    // Step 3 — Create final public version
    const step3Completed = step2Completed && !canCreatePublic;
    const step3Active = step2Completed && canCreatePublic;
    const step3Disabled = !step2Completed;

    return (
      <Grid.Column className="pb-20 pt-0">
        <Divider horizontal>
          <Header as="h4">{i18next.t("Approval request workflow")}</Header>
        </Divider>

        <Step.Group
          ordered
          vertical
          fluid
          size="mini"
          className="ep-step-group"
        >
          {/* Step 1 — Request for approval */}
          <Step completed={step1Completed} active={step1Active}>
            <Step.Content>
              <div className="ep-action-step">
                <div>
                  <Step.Title>{i18next.t("Request for approval")}</Step.Title>
                  <Step.Description>
                    {isDeclined ? (
                      <>
                        {i18next.t("Request was declined.")}
                        {requestLink && (
                          <>
                            {" "}
                            <a
                              href={requestLink}
                              target="_blank"
                              rel="noreferrer"
                            >
                              {i18next.t("View")}
                              <Icon
                                name="external alternate"
                                className="ml-5"
                              />
                            </a>
                          </>
                        )}
                      </>
                    ) : step1Completed ? (
                      i18next.t("Request submitted.")
                    ) : (
                      i18next.t("Submit the document for EP committee review.")
                    )}
                  </Step.Description>
                </div>
                {canResubmit && (
                  <Button
                    positive
                    size="mini"
                    onClick={() => this.setState({ submitModalOpen: true })}
                  >
                    {isDeclined
                      ? i18next.t("Request again")
                      : i18next.t("Request approval")}
                  </Button>
                )}
              </div>
            </Step.Content>

            {canResubmit && (
              <EPApprovalSubmitModal
                open={submitModalOpen}
                record={record}
                receiverGroup={receiver_group}
                onClose={() => this.setState({ submitModalOpen: false })}
                onSuccess={this.handleSubmitSuccess}
              />
            )}
          </Step>

          {/* Step 2 — EP Board review */}
          <Step
            completed={step2Completed}
            active={step2Active}
            disabled={step2Disabled}
          >
            <Step.Content>
              <div className="ep-action-step">
                <div>
                  <Step.Title>{i18next.t("EP Board review")}</Step.Title>
                  <Step.Description>
                    {step2Completed ? (
                      requestLink ? (
                        <a href={requestLink} target="_blank" rel="noreferrer">
                          {i18next.t("Approved as {{rn}}", {
                            rn: approved_report_number,
                          })}
                          <Icon name="external alternate" className="ml-5" />
                        </a>
                      ) : (
                        i18next.t("Approved as {{rn}}", {
                          rn: approved_report_number,
                        })
                      )
                    ) : (
                      i18next.t(
                        "The EP secretariat will review the submission."
                      )
                    )}
                  </Step.Description>
                </div>
                {step2Active && requestLink && (
                  <Button
                    as="a"
                    size="mini"
                    href={requestLink}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {i18next.t("View request")}
                    <Icon name="external alternate" className="ml-5" />
                  </Button>
                )}
              </div>
            </Step.Content>
          </Step>

          {/* Step 3 — Create final public version */}
          <Step
            completed={step3Completed}
            active={step3Active}
            disabled={step3Disabled}
          >
            <Step.Content>
              <div className="ep-action-step">
                <div>
                  <Step.Title>
                    {i18next.t("Create final public version")}
                  </Step.Title>
                  <Step.Description>
                    {step3Completed ? (
                      resolvedPublicRecordUrl ? (
                        <a
                          href={resolvedPublicRecordUrl}
                          target="_blank"
                          rel="noreferrer"
                        >
                          {i18next.t("View public record")}
                          <Icon name="external alternate" className="ml-5" />
                        </a>
                      ) : (
                        i18next.t("Public record created.")
                      )
                    ) : (
                      i18next.t(
                        "Publish the EP-approved record publicly on CDS."
                      )
                    )}
                  </Step.Description>
                </div>
                {step3Active && (
                  <Button
                    primary
                    size="mini"
                    onClick={() =>
                      this.setState({ createPublicModalOpen: true })
                    }
                  >
                    {i18next.t("Publish")}
                  </Button>
                )}
              </div>
            </Step.Content>
            {step3Active && (
              <CreatePublicRecordModal
                open={createPublicModalOpen}
                record={record}
                approvedReportNumber={approved_report_number}
                onClose={() => this.setState({ createPublicModalOpen: false })}
                onSuccess={this.handlePublicRecordCreated}
              />
            )}
          </Step>
        </Step.Group>

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

EPApprovalManageSection.propTypes = {
  record: PropTypes.object.isRequired,
};
