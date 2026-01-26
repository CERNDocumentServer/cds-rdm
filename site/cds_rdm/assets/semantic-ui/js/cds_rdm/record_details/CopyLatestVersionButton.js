import React from "react";
import PropTypes from "prop-types";
import { i18next } from "@translations/invenio_app_rdm/i18next";
import ReactDOM from "react-dom";
import { CopyButton } from "@js/invenio_app_rdm/components/CopyButton";

export const CopyLatestVersionButton = ({ text }) => {
  return (
    <CopyButton
      basic
      className="pt-10 pb-10 mr-0"
      size="tiny"
      icon="linkify"
      labelPosition="right"
      content={i18next.t("Copy latest version link")}
      text={text}
    />
  );
};

CopyLatestVersionButton.propTypes = {
  text: PropTypes.string.isRequired,
};

const domContainer = document.getElementById("copy-latesst-version-button");
const text = JSON.parse(domContainer.dataset.text);

ReactDOM.render(<CopyLatestVersionButton text={text} />, domContainer);
