// This file is part of CDS-RDM
// Copyright (C) 2026 CERN.
//
// CDS-RDM is free software; you can redistribute it and/or modify it
// under the terms of the GPL-2.0 License; see LICENSE file for more details.

import React from "react";
import { withState } from "react-searchkit";
import { Button, Icon } from "semantic-ui-react";
import { i18next } from "@translations/invenio_administration/i18next";
import { extractRunIdFromQuery } from "./utils";

const DownloadButtonComponent = ({ currentQueryState }) => {
  const domContainer = document.getElementById("invenio-search-config");
  const runs = JSON.parse(domContainer?.dataset.harvesterRuns || "[]");

  const runId = extractRunIdFromQuery(
    currentQueryState.queryString || "",
    runs
  );

  const handleDownload = () => {
    if (!runId) return;
    const params = new URLSearchParams({ run_id: runId });
    window.location.href = `/harvester-reports/download?${params.toString()}`;
  };

  return (
    <Button
      icon
      labelPosition="left"
      onClick={handleDownload}
      disabled={!runId}
      className="harvester-download-button"
      size="small"
    >
      <Icon name="download" />
      {i18next.t("Download")}
    </Button>
  );
};

export const DownloadButton = withState(DownloadButtonComponent);
