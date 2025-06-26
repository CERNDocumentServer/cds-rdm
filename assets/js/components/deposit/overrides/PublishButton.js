// This file is part of CDS RDM
// Copyright (C) 2025 CERN.
//
// CDS RDM is free software; you can redistribute it and/or modify it
// under the terms of the MIT License; see LICENSE file for more details.

import { i18next } from "@translations/invenio_rdm_records/i18next";
import {
  PublishOrSubmitModalFormFields,
  parameters,
} from "./SubmitReviewModal";
import { Formik } from "formik";
import React from "react";
import { Form } from "semantic-ui-react";
import PropTypes from "prop-types";
import { Button, Icon, Message, Modal } from "semantic-ui-react";

export class PublishModalComponent extends React.Component {
  render() {
    const {
      isConfirmModalOpen,
      handleSubmitRecord,
      buttonLabel,
      publishWithoutCommunity,
      publishModalExtraContent,
      closeConfirmModal,
      handlePublish,
    } = this.props;

    const { confirmSubmitReviewSchema, formikDefaults } = parameters;

    return (
      <Formik
        initialValues={formikDefaults}
        onSubmit={(values) =>
          handlePublish(values, handleSubmitRecord, publishWithoutCommunity)
        }
        validationSchema={confirmSubmitReviewSchema}
        validateOnChange={false}
        validateOnBlur={false}
      >
        {({ values, handleSubmit }) => {
          return (
            <Modal
              open={isConfirmModalOpen}
              onClose={closeConfirmModal}
              size="small"
              closeIcon
              closeOnDimmerClick={false}
            >
              <Modal.Header>
                {i18next.t("Are you sure you want to publish this record?")}
              </Modal.Header>
              <Modal.Content>
                <Message visible warning>
                  <p>
                    <Icon name="warning sign" />{" "}
                    {i18next.t(
                      "Once the record is published you will no longer be able to change the files in the upload! However, you will still be able to update the record's metadata later."
                    )}
                  </p>
                </Message>
                <Form>
                  <PublishOrSubmitModalFormFields />
                </Form>
                {publishModalExtraContent && (
                  <div
                    dangerouslySetInnerHTML={{
                      __html: publishModalExtraContent,
                    }}
                  />
                )}
              </Modal.Content>
              <Modal.Actions>
                <Button onClick={closeConfirmModal} floated="left">
                  {i18next.t("Cancel")}
                </Button>
                <Button
                  onClick={(event) => handleSubmit(event)}
                  positive
                  content={buttonLabel}
                />
              </Modal.Actions>
            </Modal>
          );
        }}
      </Formik>
    );
  }
}

PublishModalComponent.propTypes = {
  isConfirmModalOpen: PropTypes.bool.isRequired,
  handleSubmitRecord: PropTypes.func.isRequired,
  buttonLabel: PropTypes.string,
  publishWithoutCommunity: PropTypes.bool,
  publishModalExtraContent: PropTypes.string,
  closeConfirmModal: PropTypes.func.isRequired,
  handlePublish: PropTypes.func.isRequired,
};

PublishModalComponent.defaultProps = {
  buttonLabel: i18next.t("Publish"),
  publishWithoutCommunity: false,
  publishModalExtraContent: undefined,
};
