// This file is part of CDS-RDM
// Copyright (C) 2026 CERN.
//
// CDS-RDM is free software; you can redistribute it and/or modify it
// under the terms of the GPL-2.0 License; see LICENSE file for more details.

import React from "react";
import { Icon } from "semantic-ui-react";

export const buildTimestampFilter = (run) => {
  if (!run || !run.started_at) return "";

  const startTime = run.started_at;
  const endTime = run.finished_at || "*";

  return `@timestamp:["${startTime}" TO "${endTime}"]`;
};


export const getStatusColor = (status) => {
  const statusMap = {
    S: "green",
    SUCCESS: "green",
    F: "red",
    FAILURE: "red",
    R: "yellow",
    RUNNING: "yellow",
    C: "orange",
    CANCELLED: "orange",
    Q: "grey",
    QUEUED: "grey",
    P: "yellow",
    PARTIAL_SUCCESS: "yellow",
  };
  return statusMap[status?.toUpperCase()] || "grey";
};

export const getStatusIcon = (status) => {
  const statusMap = {
    S: "check circle",
    SUCCESS: "check circle",
    F: "times circle",
    FAILURE: "times circle",
    R: "spinner",
    RUNNING: "spinner",
    C: "ban",
    CANCELLED: "ban",
    Q: "clock outline",
    QUEUED: "clock outline",
    P: "warning sign",
    PARTIAL_SUCCESS: "warning sign",
  };
  return statusMap[status?.toUpperCase()] || "circle outline";
};

/**
 * Extract run ID from query string by matching timestamp filter
 */
export const extractRunIdFromQuery = (queryString, runs) => {
  if (!queryString || !runs || runs.length === 0) return null;

  const timestampMatch = queryString.match(/@timestamp:\["?([^"\]]+)"?\s+TO\s+"?([^"\]]+|\*)"?\]/);
  if (!timestampMatch) return null;

  const [, startTime, endTime] = timestampMatch;

  return runs.find((run) => {
    const runEndTime = run.finished_at || "*";
    return run.started_at === startTime && runEndTime === endTime;
  })?.id || null;
};

/**
 * Format run for display in dropdown
 */
export const formatRunOption = (run) => {
  const date = new Date(run.started_at);
  const dateStr = date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

  return {
    key: run.id,
    value: run.id,
    text: dateStr,
    content: (
      <div className="harvester-run-option">
        <Icon name={getStatusIcon(run.status)} color={getStatusColor(run.status)} />
        <div>
          <div>{dateStr}</div>
          {run.message && (
            <div className="run-message-preview">
              {run.message}
            </div>
          )}
        </div>
      </div>
    ),
  };
};
