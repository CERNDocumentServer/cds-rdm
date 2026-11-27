// This file is part of CDS RDM
// Copyright (C) 2026 CERN.
//
// CDS RDM is free software; you can redistribute it and/or modify it
// under the terms of the GPL-2.0 License; see LICENSE file for more details.

import { CommitteeApprovalManageSection } from "../CommitteeApproval";
import { CLCSync } from "../clc_sync";

export const RecordManagementContainer = (props) => (
  <>
    <CLCSync {...props} />
    <CommitteeApprovalManageSection {...props} />
  </>
);
