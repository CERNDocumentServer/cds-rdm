/*
 * This file is part of Invenio.
 * Copyright (C) 2016-2022 CERN.
 *
 * Invenio is free software; you can redistribute it and/or modify it
 * under the terms of the MIT License; see LICENSE file for more details.
 */

import React from "react";
import PropTypes from "prop-types";
import { i18next } from "@translations/invenio_communities/i18next";
import {
  Transition,
  Container,
  Grid,
  Header,
  Item,
  Icon,
} from "semantic-ui-react";
import _isEmpty from "lodash/isEmpty";

export const CDSCommunitiesCarousel = ({
  data,
  animationDirection,
  activeIndex,
  title,
  animationSpeed,
  carouselSlides,
  stopCarousel,
  startCarousel,
  runCarousel,
}) => {
  return (
    !_isEmpty(data.hits) && (
      <Container
        fluid
        className="carousel rel-pt-2 rel-pb-2 ml-0-mobile mr-0-mobile"
      >
        {title && (
          <Container className="rel-mb-3 full-width">
            <div className="max-width-computer center">
              <Header as="h2">
                {title}
              </Header>
            </div>
          </Container>
        )}
        <div className="full-width metadata-background-color">
          <Grid
            container
            onFocus={stopCarousel}
            onBlur={startCarousel}
            className="max-width-computer"
          >
            <Grid.Column
              mobile={2}
              tablet={1}
              computer={1}
              className="pr-0"
              verticalAlign="middle"
              textAlign="left"
            >
              <Icon
                className="carousel-arrow"
                inverted
                role="button"
                name="angle left"
                size="huge"
                aria-label={i18next.t("Previous slide")}
                onClick={() => runCarousel(activeIndex - 1)}
                onKeyDown={(event) =>
                  event.key === "Enter" && runCarousel(activeIndex - 1)
                }
                tabIndex="0"
              />
            </Grid.Column>

            <Grid.Column
              mobile={12}
              tablet={14}
              computer={14}
              className="flex align-items-center"
            >
              <Transition.Group
                as={Item.Group}
                className="flex align-items-center justify-center"
                duration={animationSpeed}
                animation={`carousel-slide ${animationDirection}`}
                directional
              >
                {carouselSlides}
              </Transition.Group>
            </Grid.Column>

            <Grid.Column
              mobile={2}
              tablet={1}
              computer={1}
              className="pl-0"
              verticalAlign="middle"
              textAlign="right"
            >
              <Icon
                className="carousel-arrow"
                inverted
                role="button"
                name="angle right"
                size="huge"
                aria-label={i18next.t("Next slide")}
                onClick={() => runCarousel(activeIndex + 1)}
                onKeyDown={(event) =>
                  event.key === "Enter" && runCarousel(activeIndex + 1)
                }
                tabIndex="0"
              />
            </Grid.Column>
          </Grid>
        </div>
      </Container>
    )
  );
};

CDSCommunitiesCarousel.propTypes = {
  data: PropTypes.object.isRequired,
  animationDirection: PropTypes.string.isRequired,
  activeIndex: PropTypes.number.isRequired,
  title: PropTypes.string.isRequired,
  animationSpeed: PropTypes.number.isRequired,
  carouselSlides: PropTypes.array.isRequired,
  stopCarousel: PropTypes.func.isRequired,
  startCarousel: PropTypes.func.isRequired,
  runCarousel: PropTypes.func.isRequired,
};
