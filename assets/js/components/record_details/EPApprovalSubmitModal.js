// This file is part of CDS RDM
// Copyright (C) 2025 CERN.
//
// CDS RDM is free software; you can redistribute it and/or modify it
// under the terms of the GPL-2.0 License; see LICENSE file for more details.

import React, { Component } from "react";
import PropTypes from "prop-types";
import {
  Button,
  Checkbox,
  Form,
  Header,
  Message,
  Modal,
} from "semantic-ui-react";
import { http } from "react-invenio-forms";
import { i18next } from "@translations/invenio_app_rdm/i18next";

const buildInitialForm = (record) => ({
  rapid_approval: false,
  cb_review_completed: false,
  cb_process_type: "",
  paper_signed: true,
  num_non_signers: 0,
  controversy: false,
  additional_communication: "",
});

export class EPApprovalSubmitModal extends Component {
  constructor(props) {
    super(props);
    this.state = {
      form: buildInitialForm(props.record),
      submitting: false,
      error: null,
    };
  }

  handleChange = (e, { name, value, checked, type }) => {
    this.setState((prev) => ({
      form: {
        ...prev.form,
        [name]: type === "checkbox" ? checked : value,
      },
    }));
  };

  handleSubmit = async () => {
    const { record, receiverGroup, onSuccess } = this.props;
    const { form } = this.state;

    this.setState({ submitting: true, error: null });
    try {
      const payload = {
        title: `Request approval for ${record["title"]}`,
        receiver_group: receiverGroup,
        payload: { ...form },
      };
      const response = await http.post(
        `/api/records/${record.id}/ep-approval`,
        payload,
        { headers: { "Content-Type": "application/json" } }
      );
      onSuccess(response.data);
    } catch (err) {
      const msg =
        err?.response?.data?.message ||
        i18next.t("An error occurred. Please try again.");
      this.setState({ error: msg });
    } finally {
      this.setState({ submitting: false });
    }
  };

  handleClose = () => {
    const { onClose, record } = this.props;
    this.setState({ form: buildInitialForm(record), error: null });
    onClose();
  };

  render() {
    const { open } = this.props;
    const { form, submitting, error } = this.state;

    return (
      <Modal open={open} onClose={this.handleClose} size="small" closeIcon>
        <Header content={i18next.t("Request for approval")} />
        <Modal.Content>
          {error && <Message negative content={error} />}
          <Form>
            <Form.Field>
              <Checkbox
                label={i18next.t("Request rapid approval (i.e. within 2 days)")}
                name="rapid_approval"
                checked={form.rapid_approval}
                onChange={this.handleChange}
              />
            </Form.Field>
            <Form.Field>
              <Checkbox
                label={i18next.t(
                  "The review process of the Collaboration Editorial Board has been completed"
                )}
                name="cb_review_completed"
                checked={form.cb_review_completed}
                onChange={this.handleChange}
              />
            </Form.Field>
            {form.cb_review_completed && (
              <Form.Group inline>
                <label>
                  {i18next.t("Was the process standard or accelerated?")}
                </label>
                <Form.Radio
                  label={i18next.t("Standard")}
                  name="cb_process_type"
                  value="standard"
                  checked={form.cb_process_type === "standard"}
                  onChange={this.handleChange}
                />
                <Form.Radio
                  label={i18next.t("Accelerated")}
                  name="cb_process_type"
                  value="accelerated"
                  checked={form.cb_process_type === "accelerated"}
                  onChange={this.handleChange}
                />
              </Form.Group>
            )}
            <Form.Field>
              <Checkbox
                label={i18next.t(
                  "The paper is signed by the whole Collaboration"
                )}
                name="paper_signed"
                checked={form.paper_signed}
                onChange={this.handleChange}
              />
            </Form.Field>
            {!form.paper_signed && (
              <Form.Input
                label={i18next.t("Number of people who did not sign")}
                name="num_non_signers"
                type="number"
                min={0}
                value={form.num_non_signers}
                onChange={this.handleChange}
              />
            )}
            {!form.paper_signed && (
              <Form.Field>
                <Checkbox
                  label={i18next.t(
                    "The non-signature reflects controversy about the paper within the Collaboration"
                  )}
                  name="controversy"
                  checked={form.controversy}
                  onChange={this.handleChange}
                />
              </Form.Field>
            )}
            <Form.TextArea
              label={i18next.t("Additional information")}
              name="additional_communication"
              value={form.additional_communication}
              onChange={this.handleChange}
            />
          </Form>
        </Modal.Content>
        <Modal.Actions>
          <Button onClick={this.handleClose} disabled={submitting}>
            {i18next.t("Close")}
          </Button>
          <Button
            positive
            icon="check"
            labelPosition="left"
            content={i18next.t("Request approval")}
            onClick={this.handleSubmit}
            loading={submitting}
            disabled={submitting}
          />
        </Modal.Actions>
      </Modal>
    );
  }
}

EPApprovalSubmitModal.propTypes = {
  open: PropTypes.bool.isRequired,
  record: PropTypes.object.isRequired,
  receiverGroup: PropTypes.string,
  onClose: PropTypes.func.isRequired,
  onSuccess: PropTypes.func.isRequired,
};

EPApprovalSubmitModal.defaultProps = {
  receiverGroup: null,
};
