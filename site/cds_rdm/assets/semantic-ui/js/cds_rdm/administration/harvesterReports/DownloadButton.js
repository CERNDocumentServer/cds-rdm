// This file is part of CDS-RDM
// Copyright (C) 2026 CERN.
//
// CDS-RDM is free software; you can redistribute it and/or modify it
// under the terms of the GPL-2.0 License; see LICENSE file for more details.

import React from "react";
import { Button, Icon } from "semantic-ui-react";
import { i18next } from "@translations/invenio_administration/i18next";
import PropTypes from "prop-types";

export const DownloadButton = ({ runId }) => (
  <div className="ui horizontal list">
    <div className="item">
      <Button
        icon
        labelPosition="left"
        onClick={() => {
          if (!runId) return;
          const q = new URLSearchParams({ run_id: runId });
          window.location.href = `/harvester-reports/download?${q}`;
        }}
        disabled={!runId}
        className="harvester-download-log-button"
        size="small"
      >
        <Icon name="download" />
        {i18next.t("Download error logs")}
      </Button>
    </div>
    <div className="item">
      <Button
        icon
        labelPosition="left"
        onClick={() => {
          if (!runId) return;
          window.location.assign(`/administration/harvester-reports/${runId}/report`);
        }}
        disabled={!runId}
        className="harvester-view-logs-button"
        size="small"
      >
        <Icon name="file alternate outline" />
        {i18next.t("View error logs")}
      </Button>
    </div>
  </div>
);

DownloadButton.propTypes = {
  runId: PropTypes.string.isRequired,
};
