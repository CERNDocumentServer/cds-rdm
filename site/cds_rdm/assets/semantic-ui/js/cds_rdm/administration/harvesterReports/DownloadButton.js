// This file is part of CDS-RDM
// Copyright (C) 2026 CERN.
//
// CDS-RDM is free software; you can redistribute it and/or modify it
// under the terms of the GPL-2.0 License; see LICENSE file for more details.

import React from "react";
import { withState } from "react-searchkit";
import { Button, Icon } from "semantic-ui-react";
import { i18next } from "@translations/invenio_administration/i18next";

const DownloadButtonComponent = ({ currentQueryState }) => {
  const handleDownload = () => {
    const query = currentQueryState.queryString || "";
    const hiddenParams = currentQueryState.hiddenParams || [];

    const params = new URLSearchParams();
    if (query) params.set("q", query);
    hiddenParams.forEach(([key, value]) => params.append(key, value));

    const downloadUrl = `/harvester-reports/download?${params.toString()}`;
    window.location.href = downloadUrl;
  };

  return (
    <Button
      icon
      labelPosition="left"
      onClick={handleDownload}
      className="harvester-download-button"
      size="small"
    >
      <Icon name="download" />
      {i18next.t("Download")}
    </Button>
  );
};

export const DownloadButton = withState(DownloadButtonComponent);
