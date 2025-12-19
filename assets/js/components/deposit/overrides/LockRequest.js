// This file is part of CDS RDM
// Copyright (C) 2025 CERN.
//
// CDS RDM is free software; you can redistribute it and/or modify it
// under the terms of the GPL-2.0 License; see LICENSE file for more details.

import React from "react";
import { i18next } from "@translations/invenio_rdm_records/i18next";
import { LockRequest } from "@js/invenio_requests/request/LockRequest";
import { parametrize } from "react-overridable";

export const parameters = {
  lockHelpText: i18next.t(
    "Locking the conversation will prevent users with access from adding/updating comments, but will still allow them to reply."
  ),
  unlockHelpText: i18next.t(
    "Unlocking the conversation will allow users with access to add/update or reply to comments."
  ),
};

export const LockRequestComponent = parametrize(LockRequest, parameters);
