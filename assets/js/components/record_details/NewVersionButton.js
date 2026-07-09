// This file is part of CDS RDM
// Copyright (C) 2026 CERN.
//
// CDS RDM is free software; you can redistribute it and/or modify it
// under the terms of the GPL-2.0 License; see LICENSE file for more details.

import PropTypes from "prop-types";
import React, { useCallback, useMemo, useState } from "react";
import { http } from "react-invenio-forms";
import { Button, Icon, Modal, Popup } from "semantic-ui-react";
import { i18next } from "@translations/invenio_rdm_records/i18next";

export const NewVersionButton = ({ onError, record, disabled, ...uiProps }) => {
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);

  const committeeApprovalStatus = useMemo(() => {
    const recordManagementDiv = document.getElementById("recordManagement");
    return recordManagementDiv
      ? JSON.parse(recordManagementDiv.dataset.committeeApproval || "null")
          ?.open_request?.status
      : null;
  }, []);

  const handleClick = useCallback(async () => {
    if (
      ["submitted", "accepted"].includes(committeeApprovalStatus) &&
      !showModal
    ) {
      // If a request exists, we discourage creating a new version.
      // This applies even if the request has been accepted.
      setShowModal(true);
      return;
    } else if (showModal) {
      setShowModal(false);
    }

    setLoading(true);
    try {
      const response = await http.post(record.links.versions);
      window.location = response.data.links.self_html;
    } catch (error) {
      console.error(error);
      setLoading(false);
      onError(error.response.data.message);
    }
  }, [committeeApprovalStatus, record, onError, showModal]);

  return (
    <>
      <Popup
        content={i18next.t(
          "You don't have permissions to create a new version."
        )}
        position="top center"
        disabled={!disabled}
        trigger={
          // Extra span needed since disabled buttons do not trigger hover events
          <span>
            <Button
              type="button"
              positive
              size="mini"
              onClick={handleClick}
              loading={loading}
              icon
              labelPosition="left"
              disabled={disabled}
              {...uiProps}
            >
              <Icon name="tag" />
              {i18next.t("New version")}
            </Button>
          </span>
        }
      />

      <Modal open={showModal} onClose={() => setShowModal(false)} size="small">
        <Modal.Header>
          <Icon name="warning sign" color="yellow" className="mr-10" />

          {committeeApprovalStatus === "submitted" &&
            i18next.t("EP approval request pending")}
          {committeeApprovalStatus === "accepted" &&
            i18next.t("EP approval already complete")}
        </Modal.Header>
        <Modal.Content>
          {committeeApprovalStatus === "submitted" && (
            <>
              <p>
                {i18next.t(
                  "An EP approval request is already pending for an existing version of this record. " +
                    "A new version will not be taken into account for the approval request."
                )}
              </p>
              <p>
                {i18next.t(
                  "Creating a new version while the request is pending is not recommended."
                )}
              </p>
            </>
          )}
          {committeeApprovalStatus === "accepted" && (
            <p>
              {i18next.t(
                "A version of this record has already been approved. Creating a new version following an approved request is not recommended."
              )}
            </p>
          )}
        </Modal.Content>
        <Modal.Actions>
          <Button onClick={() => setShowModal(false)}>
            {i18next.t("Cancel")}
          </Button>
          <Button primary onClick={handleClick}>
            {i18next.t("Continue anyway")}
          </Button>
        </Modal.Actions>
      </Modal>
    </>
  );
};

NewVersionButton.propTypes = {
  onError: PropTypes.func.isRequired,
  record: PropTypes.object.isRequired,
  disabled: PropTypes.bool,
};

NewVersionButton.defaultProps = {
  disabled: false,
};
