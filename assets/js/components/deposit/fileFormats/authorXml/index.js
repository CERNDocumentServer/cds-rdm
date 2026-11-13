// This file is part of CDS RDM
// Copyright (C) 2026 CERN.
//
// CDS RDM is free software; you can redistribute it and/or modify it
// under the terms of the GPL-2.0 License; see LICENSE file for more details.

import { i18next } from "@translations/invenio_app_rdm/i18next";
import { DEFAULT_CREATIBUTOR_FILE_FORMAT_ORDER } from "@js/invenio_rdm_records";
import { parseAuthorXml } from "./parse";

const AUTHOR_XML_IMPORT_EXAMPLE = `<collaborationauthorlist
  xmlns:foaf="http://xmlns.com/foaf/0.1/"
  xmlns:cal="http://inspirehep.net/info/HepNames/tools/authors_xml/">
  <cal:organizations>
    <foaf:Organization id="a1">
      <foaf:name>CERN</foaf:name>
      <cal:orgName source="ROR">https://ror.org/01ggx4157</cal:orgName>
    </foaf:Organization>
  </cal:organizations>
  <cal:authors>
    <foaf:Person>
      <foaf:name>Jane Smith</foaf:name>
      <foaf:givenName>Jane</foaf:givenName>
      <foaf:familyName>Smith</foaf:familyName>
      <cal:authorNamePaper>J. Smith</cal:authorNamePaper>
      <cal:authorAffiliations>
        <cal:authorAffiliation organizationid="a1"/>
      </cal:authorAffiliations>
      <cal:authorids>
        <cal:authorid source="ORCID">0000-0002-1825-0097</cal:authorid>
      </cal:authorids>
    </foaf:Person>
  </cal:authors>
</collaborationauthorlist>`;

/**
 * The INSPIRE author list format (https://github.com/inspirehep/author.xml),
 * offered by the "add authors/contributors from file" dialog.
 */
export const authorXmlFileFormat = {
  id: "author_xml",
  label: i18next.t("XML (author.xml)"),
  extension: ".xml",
  // Offered after the built-in JSON format.
  order: DEFAULT_CREATIBUTOR_FILE_FORMAT_ORDER + 10,
  example: AUTHOR_XML_IMPORT_EXAMPLE,
  note: i18next.t(
    "Author identifiers are read from the ORCID, GND, ISNI and ROR sources."
  ),
  parse: parseAuthorXml,
};
