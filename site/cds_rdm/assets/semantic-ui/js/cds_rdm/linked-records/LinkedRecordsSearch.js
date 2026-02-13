// -*- coding: utf-8 -*-
//
// Copyright (C) 2025 CERN.
//
// CDS-RDM is free software; you can redistribute it and/or modify it under
// the terms of the MIT License; see LICENSE file for more details.

import React from "react";
import PropTypes from "prop-types";
import {
  ReactSearchKit,
  InvenioSearchApi,
  ResultsLoader,
  ResultsMultiLayout,
  Error,
  EmptyResults,
  Pagination,
  BucketAggregation,
  SearchBar,
  withState,
} from "react-searchkit";
import { OverridableContext } from "react-overridable";
import { apiConfig } from "./api/config";
import { Segment, Container, Grid } from "semantic-ui-react";
import { ResultsListLayout } from "./components/ResultsLayout";
import { RecordListItem } from "./components/RecordItem";
import { FilterContainer, Filter, FilterValues } from "./components/Filter";
import { NoResults } from "./components/NoResults";
import { RelatedRecordsResultsLoader } from "./components/RelatedRecordsResultsLoader";

const linkedRecordsSearchAppID = "linkedRecordsSearch";

const overriddenComponents = {
  [`${linkedRecordsSearchAppID}.ResultsList.container`]: ResultsListLayout,
  [`${linkedRecordsSearchAppID}.ResultsList.item`]: RecordListItem,
  [`${linkedRecordsSearchAppID}.BucketAggregation.element`]: FilterContainer,
  [`${linkedRecordsSearchAppID}.BucketAggregationContainer.element`]: Filter,
  [`${linkedRecordsSearchAppID}.BucketAggregationValues.element`]: FilterValues,
  [`${linkedRecordsSearchAppID}.EmptyResults.element`]: NoResults,
  [`${linkedRecordsSearchAppID}.ResultsLoader.element`]: RelatedRecordsResultsLoader,
};

const SearchControls = withState(
  ({ currentQueryState, currentResultsState }) => {
    const hasResults = currentResultsState.total > 0;
    const hasUserQuery =
      currentQueryState.queryString !== "" ||
      currentQueryState.filters.length > 0;

    if (!hasResults && !hasUserQuery) {
      return null;
    }

    return (
      <Grid>
        <Grid.Row>
          <Grid.Column mobile={16} tablet={7} computer={8}>
            <SearchBar
              className="mb-10"
              placeholder="Search within linked records..."
              uiProps={{
                name: "linked-records-search",
                id: "linked-records-search-bar",
                icon: "search",
              }}
              actionProps={{
                icon: "search",
                content: null,
                "aria-label": "Search",
              }}
            />
          </Grid.Column>
          <Grid.Column mobile={16} tablet={9} computer={8}>
            <div className="flex align-items-center justify-end rel-mobile-pt-1">
              <BucketAggregation
                agg={{ field: "resource_type", aggName: "resource_type" }}
              />
            </div>
          </Grid.Column>
        </Grid.Row>
      </Grid>
    );
  }
);

export const LinkedRecordsSearch = ({ endpoint, searchQuery }) => {
  // Pass the base query to apiConfig so it can be handled by the request interceptor
  const searchApi = new InvenioSearchApi(apiConfig(endpoint, searchQuery));

  const initialState = {
    queryString: "", // Keep search bar empty for user input
    sortBy: "bestmatch",
    sortOrder: "asc",
    page: 1,
    size: 5,
    layout: "list",
  };

  return (
    <OverridableContext.Provider value={overriddenComponents}>
      <ReactSearchKit
        appName={linkedRecordsSearchAppID}
        searchApi={searchApi}
        urlHandlerApi={{ enabled: false }}
        initialQueryState={initialState}
      >
        <>
          {/* Search Bar and Controls */}
          <SearchControls />

          {/* Results */}
          <Segment>
            <ResultsLoader>
              <ResultsMultiLayout />
              <Error />
              <EmptyResults />
              <Container align="center" className="rel-pt-1">
                <Pagination options={{ size: "mini", showEllipsis: true }} />
              </Container>
            </ResultsLoader>
          </Segment>
        </>
      </ReactSearchKit>
    </OverridableContext.Provider>
  );
};

LinkedRecordsSearch.propTypes = {
  endpoint: PropTypes.string.isRequired,
  searchQuery: PropTypes.string.isRequired,
};
