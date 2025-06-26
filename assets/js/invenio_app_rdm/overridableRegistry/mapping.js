// This file is part of CDS RDM
// Copyright (C) 2025 CERN.
//
// CDS RDM is free software; you can redistribute it and/or modify it
// under the terms of the MIT License; see LICENSE file for more details.

import { BasicCERNInformation } from "../../components/deposit/BasicInformation";
import { CDSCarouselItem } from "../../components/communities_carousel/overrides/CarouselItem";
import { CDSRecordsList } from "../../components/frontpage/overrides/RecordsList";
import { CDSRecordsResultsListItem } from "../../components/frontpage/overrides/RecordsResultsListItem";
import { CDSRecordsResultsListItemDescription } from "../../components/search/overrides/CDSRecordsResultsListItemDescription";
import { CDSAffiliationsSuggestions } from "../../components/deposit/overrides/CDSAffiliationsSuggestions";
import { CLCSync } from "../../components/record_details/clc_sync";
import {
  SubmitReviewModalComponent,
  PublishOrSubmitModalFormFields,
} from "../../components/deposit/overrides/SubmitReviewModal";
import { PublishModalComponent } from "../../components/deposit/overrides/PublishButton";

export const overriddenComponents = {
  "InvenioAppRdm.RecordsList.layout": CDSRecordsList,
  "InvenioAppRdm.RecordsResultsListItem.layout": CDSRecordsResultsListItem,
  "InvenioCommunities.CommunitiesCarousel.layout": null,
  "InvenioCommunities.CarouselItem.layout": CDSCarouselItem,
  "InvenioAppRdm.Deposit.BasicInformation.after.container":
    BasicCERNInformation,
  "InvenioAppRdm.Deposit.CustomFields.container": () => null,
  "ReactInvenioForms.AffiliationsSuggestions.content":
    CDSAffiliationsSuggestions,
  "InvenioAppRdm.Search.RecordsResultsListItem.description":
    CDSRecordsResultsListItemDescription,
  "InvenioAppRdm.RecordLandingPage.RecordManagement.container": CLCSync,
  "InvenioRdmRecords.SubmitReviewModal.container": SubmitReviewModalComponent,
  "InvenioRdmRecords.SubmitReviewModal.Form.ExtraComponent.container":
    PublishOrSubmitModalFormFields,
  "InvenioRdmRecords.PublishModal.container": PublishModalComponent,
};
