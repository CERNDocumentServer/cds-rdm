// This file is part of CDS RDM
// Copyright (C) 2025 CERN.
//
// CDS RDM is free software; you can redistribute it and/or modify it
// under the terms of the MIT License; see LICENSE file for more details.

import React from "react";
import { i18next } from "@translations/invenio_rdm_records/i18next";
import { SubmitReviewModal, PublishModal } from "@js/invenio_rdm_records";
import { parametrize } from "react-overridable";

export const parameters = {
  extraCheckboxes: [
    {
      fieldPath: "acceptTermsOfService",
      text: (
        <>
          {i18next.t("By publishing, you agree that the record complies with")}{" "}
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
        </>
      ),
    },
  ],
};

export const SubmitReviewModalComponent = parametrize(
  SubmitReviewModal,
  parameters
);

export const PublishModalComponent = parametrize(PublishModal, parameters);
