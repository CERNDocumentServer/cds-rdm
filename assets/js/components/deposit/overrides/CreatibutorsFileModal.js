// This file is part of CDS RDM
// Copyright (C) 2026 CERN.
//
// CDS RDM is free software; you can redistribute it and/or modify it
// under the terms of the GPL-2.0 License; see LICENSE file for more details.

import { CreatibutorsFileModal, jsonFileFormat } from "@js/invenio_rdm_records";
import { parametrize } from "react-overridable";
import { authorXmlFileFormat } from "../fileFormats/authorXml";

// Add support for the author.xml format to the CreatibutorsFileModal component.
export const CreatibutorsFileModalComponent = parametrize(CreatibutorsFileModal, {
  fileFormats: [jsonFileFormat, authorXmlFileFormat],
});
