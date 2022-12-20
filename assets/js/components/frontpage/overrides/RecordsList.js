// This file is part of CDS RDM
// Copyright (C) 2022 CERN.
//
// CDS RDM is free software; you can redistribute it and/or modify it
// under the terms of the MIT License; see LICENSE file for more details.

import _get from "lodash/get";
import _truncate from "lodash/truncate";
import _upperCase from "lodash/upperCase";
import React, { Component } from "react";
import PropTypes from "prop-types";
import { withCancel, http } from "react-invenio-forms";
import {
  Loader,
  Container,
  Header,
  Item,
  Button,
  Message,
} from "semantic-ui-react";
import { RecordsResultsListItem } from "./RecordsResultsListItem";

export class RecordsList extends Component {
  constructor(props) {
    super(props);

    this.state = {
      data: { hits: [] },
      isLoading: false,
      error: null,
    };
  }

  componentDidMount() {
    this.fetchData();
  }

  componentWillUnmount() {
    this.cancellableFetch && this.cancellableFetch.cancel();
  }

  fetchData = async () => {
    const { fetchUrl } = this.props;
    this.setState({ isLoading: true });

    this.cancellableFetch = withCancel(
      http.get(fetchUrl, {
        headers: {
          Accept: "application/vnd.inveniordm.v1+json",
        },
      })
    );

    try {
      const response = await this.cancellableFetch.promise;
      this.setState({ data: response.data.hits, isLoading: false });
    } catch (error) {
      console.error(error);
      this.setState({
        error: "Unable to load records",
        isLoading: false,
      });
    }
  };

  render() {
    const { isLoading, data, error } = this.state;
    const { title } = this.props;

    const listItems = data.hits?.map((record) => {
      return <RecordsResultsListItem result={record} key={record.id} />;
    });

    return (
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
    );
  }
}

RecordsList.propTypes = {
  title: PropTypes.string.isRequired,
  fetchUrl: PropTypes.string.isRequired,
};
