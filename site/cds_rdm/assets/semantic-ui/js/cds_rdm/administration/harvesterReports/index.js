// This file is part of CDS-RDM
// Copyright (C) 2026 CERN.
//
// CDS-RDM is free software; you can redistribute it and/or modify it
// under the terms of the GPL-2.0 License; see LICENSE file for more details.

import { initDefaultSearchComponents } from "@js/invenio_administration";
import { createSearchAppInit } from "@js/invenio_search_ui";
import { NotificationController } from "@js/invenio_administration";
import { SearchFacets } from "@js/invenio_administration";
import { SearchBar } from "react-searchkit";
import { SearchResultItemLayout } from "@js/invenio_app_rdm/administration/auditLogs/search";
import { AuditLogActions } from "@js/invenio_app_rdm/administration/auditLogs/AuditLogActions";
import { HarvesterSearchBarElement } from "./SearchBar";
import { CustomEmptyResults } from "./EmptyResults";

const domContainer = document.getElementById("invenio-search-config");
if (domContainer) {
  const defaultComponents = initDefaultSearchComponents(domContainer);

  const overriddenComponents = {
    ...defaultComponents,
    "InvenioAdministration.SearchResultItem.layout": SearchResultItemLayout,
    "SearchApp.facets": SearchFacets,
    "InvenioAdministration.ResourceActions": AuditLogActions,
    "SearchBar.element": HarvesterSearchBarElement,
    "EmptyResults.element": CustomEmptyResults,
    "SearchApp.searchbarContainer": SearchBar,
  };

  createSearchAppInit(
    overriddenComponents,
    true, // autoInit
    "invenio-search-config",
    false, // searchApiAvailable
    NotificationController
  );
}
