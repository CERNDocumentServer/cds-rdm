// This file is part of CDS RDM
// Copyright (C) 2026 CERN.
//
// CDS RDM is free software; you can redistribute it and/or modify it
// under the terms of the GPL-2.0 License; see LICENSE file for more details.

// Formats offered by the deposit form's "add authors/contributors from file"
// dialog, in addition to the built-in JSON format. Imported for its side effect
// by the overridable registry, which the deposit page loads.

import {
  getCreatibutorFileFormats,
  registerCreatibutorFileFormat,
} from "@js/invenio_rdm_records";
import { authorXmlFileFormat } from "./authorXml";

const isRegistered = ({ id }) =>
  getCreatibutorFileFormats().some((format) => format.id === id);

// Registering is idempotent, so evaluating this module twice does not throw.
[authorXmlFileFormat].forEach((fileFormat) => {
  if (!isRegistered(fileFormat)) registerCreatibutorFileFormat(fileFormat);
});
