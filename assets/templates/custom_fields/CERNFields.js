// This file is part of Invenio-RDM-Records
// Copyright (C) 2020-2023 CERN.
// Copyright (C) 2020-2022 Northwestern University.
//
// Invenio-RDM-Records is free software; you can redistribute it and/or modify it
// under the terms of the GPL-2.0 License; see LICENSE file for more details.

import React, { Component } from "react";

import { FieldLabel } from "react-invenio-forms";
import { Divider, Grid } from "semantic-ui-react";

import PropTypes from "prop-types";
import { AccordionField } from "react-invenio-forms";

export class CERNFields extends Component {
  feedbackCfg = {
    "cern-information-section": [
      "custom_fields.cern:programmes",
      "custom_fields.cern:administrative_unit",
      "custom_fields.cern:department",
      "custom_fields.cern:experiments",
      "custom_fields.cern:accelerators",
      "custom_fields.cern:beams",
      "custom_fields.cern:projects",
      "custom_fields.cern:studies",
      "custom_fields.cern:facilities",
    ],
  };

  render() {
    const { key, children, label, active } = this.props;
    const [
      department,
      administrativeUnit,
      programme,
      accelerator,
      experiment,
      projects,
      studies,
      facilities,
      beam,
    ] = children;
    return (
      <AccordionField
        key={key}
        includesPaths={this.feedbackCfg["cern-information-section"]}
        label={label}
        active={active}
        id="cern-information-section"
      >
        <Grid padded>
          <Grid.Column computer={8}>{department}</Grid.Column>
          <Grid.Column computer={8}>{administrativeUnit}</Grid.Column>
          <Grid.Column computer={16}>{programme}</Grid.Column>
        </Grid>
        <FieldLabel htmlFor="CERNFields" icon="bullseye" label="Physics" />
        <Divider fitted />
        <Grid padded>
          <Grid.Column computer={16}>{experiment}</Grid.Column>
          <Grid.Column computer={12}>{accelerator}</Grid.Column>
          <Grid.Column computer={4}>{beam}</Grid.Column>
        </Grid>
        <FieldLabel
          htmlFor="CERNFields"
          icon="chart line"
          label="Research activities"
        />
        <Divider fitted />
        <Grid padded>
          <Grid.Column computer={16}>{projects}</Grid.Column>
          <Grid.Column computer={8}>{studies}</Grid.Column>
          <Grid.Column computer={8}>{facilities}</Grid.Column>
        </Grid>
      </AccordionField>
    );
  }
}

CERNFields.propTypes = {
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

CERNFields.defaultProps = {
  label: "CERN",
  active: true,
  key: "CERNFields",
};
