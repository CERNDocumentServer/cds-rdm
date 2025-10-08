// This file is part of CDS RDM
// Copyright (C) 2022 CERN.
//
// CDS RDM is free software; you can redistribute it and/or modify it
// under the terms of the GPL-2.0 License; see LICENSE file for more details.

import React from "react";
import PropTypes from "prop-types";
import isEmpty from "lodash/isEmpty";
import {
  Loader,
  Container,
  Header,
  Item,
  Button,
  Message,
} from "semantic-ui-react";

export const CDSRecordsList = ({ isLoading, error, title, listItems }) => {
  return (
    !isEmpty(listItems) && (
      <>
        <Container>
          {isLoading && <Loader active inline="centered" />}
        </Container>

        {!isLoading && !error && (
          <>
            <Container>
              <Header as="h2">{title}</Header>
            </Container>
            <Item.Group relaxed="very" link>
              {listItems}
            </Item.Group>
            <Container textAlign="center">
              <Button href="/search">More</Button>
            </Container>
          </>
        )}
        {error && <Message content={error} error icon="info" />}
      </>
    )
  );
};

CDSRecordsList.propTypes = {
  isLoading: PropTypes.bool.isRequired,
  error: PropTypes.string.isRequired,
  title: PropTypes.string.isRequired,
  listItems: PropTypes.array.isRequired,
};
