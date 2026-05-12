// This file is part of Invenio-RDM-Records
// Copyright (C) 2020-2023 CERN.
// Copyright (C) 2020-2022 Northwestern University.
//
// Invenio-RDM-Records is free software; you can redistribute it and/or modify it
// under the terms of the GPL-2.0 License; see LICENSE file for more details.

import React, { Component } from "react";

import { Grid } from "semantic-ui-react";

import PropTypes from "prop-types";
import { AccordionField } from "react-invenio-forms";

export class CERNPublication extends Component {
  feedbackCfg = {
    "publication-section": [
      "custom_fields.journal:journal",
      "custom_fields.cern:oa_level",
      "custom_fields.cern:oa_funding_model",
      "custom_fields.imprint:imprint",
      "custom_fields.thesis:thesis",
    ],
  };

  render() {
    const { key, children, label, active } = this.props;
    const [journal, oaLevel, oaFundingModel, imprint, thesis] = children;
    return (
      <AccordionField
        key={key}
        includesPaths={this.feedbackCfg["publication-section"]}
        label={label}
        active={active}
        id="publication-section"
      >
        {journal}
        <Grid padded>
          <Grid.Column computer={8}>{oaLevel}</Grid.Column>
          <Grid.Column computer={8}>{oaFundingModel}</Grid.Column>
        </Grid>
        {imprint}
        {thesis}
      </AccordionField>
    );
  }
}

CERNPublication.propTypes = {
  label: PropTypes.string,
  children: PropTypes.arrayOf(
    PropTypes.shape({
      field: PropTypes.string.isRequired,
      ui_widget: PropTypes.string.isRequired,
      props: PropTypes.object,
    })
  ).isRequired,
  active: PropTypes.bool,
  key: PropTypes.string,
};

CERNPublication.defaultProps = {
  label: "CERN",
  active: true,
  key: "CERNPublication",
};
