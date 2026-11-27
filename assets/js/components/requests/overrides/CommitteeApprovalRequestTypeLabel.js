// This file is part of CDS RDM
// Copyright (C) 2026 CERN.
//
// CDS RDM is free software; you can redistribute it and/or modify it
// under the terms of the GPL-2.0 License; see LICENSE file for more details.

import { DatasetContext } from "@js/invenio_requests/data";
import { i18next } from "@translations/invenio_requests/i18next";
import { useContext } from "react";
import { Label } from "semantic-ui-react";

export const CommitteeApprovalRequestTypeLabel = () => {
  const dataset = useContext(DatasetContext);
  const approvalLabel = dataset?.request?.payload?.approval_label;

  return (
    <Label horizontal className="primary theme-secondary" size="small">
      {approvalLabel || i18next.t("Committee review")}
    </Label>
  );
};
