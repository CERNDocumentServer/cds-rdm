// This file is part of CDS RDM
// Copyright (C) 2025 CERN.
//
// CDS RDM is free software; you can redistribute it and/or modify it
// under the terms of the GPL-2.0 License; see LICENSE file for more details.

import React, { Component } from "react";
import PropTypes from "prop-types";
import { Button, Checkbox, Header, Icon, Message, Modal } from "semantic-ui-react";
import { http } from "react-invenio-forms";
import { i18next } from "@translations/invenio_rdm_records/i18next";

export class CreatePublicRecordModal extends Component {
  constructor(props) {
    super(props);
    this.state = {
      submitting: false,
      error: null,
      publicRecord: null,
      alreadyExists: false,
      agreedToTerms: false,
      agreedToCommunity: false,
    };
  }

  handleCreate = async () => {
    const { record, onSuccess } = this.props;
    this.setState({ submitting: true, error: null, alreadyExists: false });
    try {
      const response = await http.post(
        `/api/records/${record.id}/ep-approval/publish-public`,
        {},
        { headers: { "Content-Type": "application/json" } }
      );
      this.setState({ publicRecord: response.data });
      onSuccess(response.data);
    } catch (err) {
      if (err?.response?.status === 409 && err?.response?.data?.id) {
        // A public record already exists — show a warning and surface the link.
        const existingRecord = err.response.data;
        this.setState({ publicRecord: existingRecord, alreadyExists: true });
        onSuccess(existingRecord);
      } else {
        const msg =
          err?.response?.data?.message ||
          i18next.t("An error occurred. Please try again.");
        this.setState({ error: msg });
      }
    } finally {
      this.setState({ submitting: false });
    }
  };

  handleClose = () => {
    const { onClose } = this.props;
    this.setState({
      error: null,
      publicRecord: null,
      agreedToTerms: false,
      agreedToCommunity: false,
    });
    onClose();
  };

  render() {
    const { open, record } = this.props;
    const {
      submitting,
      error,
      publicRecord,
      alreadyExists,
      agreedToTerms,
      agreedToCommunity,
    } = this.state;

    const versionIndex = record?.versions?.index;
    const canPublish = agreedToTerms && agreedToCommunity;

    const epApprovalEl = document.getElementById("recordManagement");
    const epApproval = epApprovalEl
      ? JSON.parse(epApprovalEl.dataset.epApproval || "null")
      : null;
    const communityId = epApproval?.cern_scientific_community_id;

    return (
      <Modal open={open} onClose={this.handleClose} size="small" closeIcon>
        <Header
          content={i18next.t(
            "Are you sure you want to create a public record of the approved document?"
          )}
        />
        <Modal.Content>
          {error && <Message negative content={error} />}

          {publicRecord && alreadyExists ? (
            <Message warning>
              <Message.Header>
                {i18next.t("A public record already exists")}
              </Message.Header>
              <Message.Content>
                {i18next.t(
                  "A public record for this approval has already been created."
                )}{" "}
                <a
                  href={publicRecord.links?.self_html}
                  target="_blank"
                  rel="noreferrer"
                >
                  {i18next.t("View public record")}
                  <Icon name="external alternate" className="ml-5" />
                </a>
              </Message.Content>
            </Message>
          ) : publicRecord ? (
            <Message positive>
              <Message.Header>{i18next.t("Public record created")}</Message.Header>
              <Message.Content>
                {i18next.t("The public record has been created successfully.")}{" "}
                <a
                  href={publicRecord.links?.self_html}
                  target="_blank"
                  rel="noreferrer"
                >
                  {i18next.t("View public record")}
                  <Icon name="external alternate" className="ml-5" />
                </a>
              </Message.Content>
            </Message>
          ) : (
            <>
              <Message visible warning>
                <p>
                  <Icon name="warning sign" />{" "}
                  {i18next.t(
                    "The metadata and files of Version v{{v}} will be copied to the new public record. Once published, the files can no longer be changed.",
                    { v: versionIndex ?? "?" }
                  )}
                </p>
              </Message>

              <Checkbox
                checked={agreedToTerms}
                onChange={(_, { checked }) => this.setState({ agreedToTerms: checked })}
                label={
                  <label>
                    {i18next.t(
                      "By publishing, you agree that the record complies with"
                    )}{" "}
                    <a
                      href="https://repository.cern/records/53y0h-6ad63"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {i18next.t("CDS Terms of Service")}
                    </a>
                    ,{" "}
                    <a
                      href="https://repository.cern/records/dd19c-hwf65"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {i18next.t("CDS Content Policy")}
                    </a>{" "}
                    {i18next.t("and")}{" "}
                    <a
                      href="https://cds.cern.ch/record/45085"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {i18next.t("OC6")}
                    </a>
                    .
                  </label>
                }
              />
              <div className="mt-10">
                <Checkbox
                  checked={agreedToCommunity}
                  onChange={(_, { checked }) =>
                    this.setState({ agreedToCommunity: checked })
                  }
                  label={
                    <label>
                      {i18next.t(
                        "Once created, the record will be automatically added to the"
                      )}{" "}
                      <a
                        href={`/communities/${communityId || "cern-research"}`}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {i18next.t("CERN Research")}
                      </a>{" "}
                      {i18next.t(
                        "community. The curators of the community will be able to curate both the metadata and files of the published record."
                      )}
                    </label>
                  }
                />
              </div>
            </>
          )}
        </Modal.Content>
        <Modal.Actions>
          <Button floated="left" onClick={this.handleClose} disabled={submitting}>
            {publicRecord ? i18next.t("Close") : i18next.t("Cancel")}
          </Button>
          {!publicRecord && (
            <Button
              positive
              content={i18next.t("Publish")}
              onClick={this.handleCreate}
              loading={submitting}
              disabled={submitting || !canPublish}
            />
          )}
        </Modal.Actions>
      </Modal>
    );
  }
}

CreatePublicRecordModal.propTypes = {
  open: PropTypes.bool.isRequired,
  record: PropTypes.object.isRequired,
  onClose: PropTypes.func.isRequired,
  onSuccess: PropTypes.func.isRequired,
};
