// This file is part of CDS RDM
// Copyright (C) 2025 CERN.
//
// CDS RDM is free software; you can redistribute it and/or modify it
// under the terms of the GPL-2.0 License; see LICENSE file for more details.

import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { i18next } from "@translations/invenio_rdm_records/i18next";
import { SubmitReviewModal, PublishModal } from "@js/invenio_rdm_records";
import { useFormikContext } from "formik";
import { useSelector } from "react-redux";
import { http } from "react-invenio-forms";
import _get from "lodash/get";
import { Message, Icon } from "semantic-ui-react";

/**
 * Informs the user about the CERN Research Community side effects of publishing.
 * The decision (include / remove / nothing) is made by the backend
 * (`get_community_inclusion_action`), so the rules live in a single place.
 *
 * Wraps the base modal so that the *deposit form* values (outer formik context)
 * can be read; the modal renders its own inner formik context.
 */
const withCommunityInclusionMessages = (Modal) => {
  // Render the original (non-overridable) modal: the registry maps the modal's
  // container id to this very component, so using the overridable one recurses.
  // `parametrize` is not used because its params win over props, which would
  // discard the conditional `extraCheckboxes` below.
  const ModalComponent = Modal.originalComponent || Modal;

  const Wrapped = (props) => {
    const { values } = useFormikContext();
    const pid = useSelector((state) => state.deposit.record?.id);
    const [action, setAction] = useState(null);

    const access = _get(values, "access.record");
    const resourceType = _get(values, "metadata.resource_type.id");

    useEffect(() => {
      let active = true;
      http
        .post("/api/cds/community-inclusion", {
          pid,
          access,
          resource_type: resourceType,
        })
        .then((response) => active && setAction(response.data?.action))
        .catch(() => active && setAction(null));
      return () => {
        active = false;
      };
    }, [pid, access, resourceType]);

    let beforeContent = props.beforeContent;
    if (action === "remove") {
      beforeContent = () => (
        <Message visible negative className="rel-mb-1">
          <p>
            <Icon name="warning sign" />
            {i18next.t(
              "You are making this record restricted. The record, including all its versions, will be removed from the CERN Research Community (or its pending inclusion request will be cancelled). Do you want to continue?"
            )}
          </p>
        </Message>
      );
    }

    const includesInCommunity = action === "include";
    return (
      <ModalComponent
        // The modals read `extraCheckboxes` once on mount, hence the `key`: it
        // remounts the modal when the (async) decision arrives.
        key={includesInCommunity ? "include" : "default"}
        {...props}
        {...parameters}
        beforeContent={beforeContent}
        extraCheckboxes={
          includesInCommunity
            ? [...parameters.extraCheckboxes, communityInclusionCheckbox]
            : parameters.extraCheckboxes
        }
      />
    );
  };
  Wrapped.propTypes = {
    beforeContent: PropTypes.func,
  };

  Wrapped.defaultProps = {
    beforeContent: undefined,
  };

  return Wrapped;
};

const communityInclusionCheckbox = {
  id: "accept-community-inclusion-checkbox",
  fieldPath: "acceptCommunityInclusion",
  text: i18next.t(
    "I understand that once published, this record will also be submitted for inclusion in the CERN Research Community."
  ),
};

export const parameters = {
  extraCheckboxes: [
    {
      id: "accept-terms-of-service-checkbox",
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

export const SubmitReviewModalComponent =
  withCommunityInclusionMessages(SubmitReviewModal);

export const PublishModalComponent = withCommunityInclusionMessages(PublishModal);
