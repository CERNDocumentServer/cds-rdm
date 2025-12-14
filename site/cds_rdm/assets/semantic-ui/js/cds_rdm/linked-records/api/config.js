// -*- coding: utf-8 -*-
//
// Copyright (C) 2025 CERN.
//
// CDS-RDM is free software; you can redistribute it and/or modify it under
// the terms of the MIT License; see LICENSE file for more details.

export const apiConfig = (endpoint, baseQuery) => ({
  axios: {
    url: endpoint,
    timeout: 5000,
    headers: {
      Accept: "application/vnd.inveniordm.v1+json",
    },
  },
  interceptors: {
    request: {
      resolve: (config) => {
        // Modify the params to combine base query with user search
        if (config.params) {
          const userQuery = config.params.queryString;

          // Combine base query with user search
          if (baseQuery && userQuery) {
            config.params.queryString = `(${baseQuery}) AND (${userQuery})`;
          } else if (baseQuery) {
            config.params.queryString = baseQuery;
          }
          // If only userQuery exists, leave it as is (though this shouldn't happen)
        }

        return config;
      },
      reject: (error) => Promise.reject(error),
    },
  },
});
