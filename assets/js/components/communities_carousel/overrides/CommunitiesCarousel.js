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
  Icon,
  Card,
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
  itemsPerPage,
}) => {
  return (
    !_isEmpty(data.hits) && (
      <Container fluid className="rel-mt-3 rel-mb-5 ml-0-mobile mr-0-mobile">
        {title && (
          <Container textAlign="right">
            <Header as="h2">{title}</Header>
          </Container>
        )}

        <Container
          onFocus={stopCarousel}
          onBlur={startCarousel}
          fluid
          className="rel-pb-2 rel-pt-3 rel-mt-4 ml-0-mobile mr-0-mobile"
        >
          <Container>
            <Grid>
              <Grid.Column
                computer={2}
                mobile={2}
                className="align-self-center"
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
                computer={13}
                mobile={12}
                className="align-self-center"
              >
                <Transition.Group
                  duration={animationSpeed}
                  visible={true}
                  animation={`fade ${animationDirection}`}
                >
                  <div className="ui three cards flex">{carouselSlides}</div>
                </Transition.Group>
              </Grid.Column>
              <Grid.Column
                computer={1}
                mobile={1}
                textAlign="right"
                className="align-self-center"
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
          </Container>
        </Container>
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
  itemsPerPage: PropTypes.number.isRequired
};
