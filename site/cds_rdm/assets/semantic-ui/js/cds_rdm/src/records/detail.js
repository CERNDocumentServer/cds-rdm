/*
 * This file is part of Invenio.
 * Copyright (C) 2016-2022 CERN.
 *
 * Invenio is free software; you can redistribute it and/or modify it
 * under the terms of the MIT License; see LICENSE file for more details.
 */

import $ from "jquery";

// Initialize conceptdoi modal
$("#record-conceptdoi-badge").on("click", function () {
  $("#conceptdoi-modal").modal("show");
});
