import { i18next } from "@translations/invenio_rdm_records/i18next";
import { SubmitReviewModal } from "@js/invenio_rdm_records";
import { useFormikContext } from "formik";
import _get from "lodash/get";
import { parametrize } from "react-overridable";
import React from "react";
import { Trans } from "react-i18next";
import { ErrorLabel, RadioField } from "react-invenio-forms";
import { Checkbox, Form } from "semantic-ui-react";
import * as Yup from "yup";

const msgWarningTos = i18next.t(
  "I accept the <link>terms of service</link> and the content policy."
);

export const PublishOrSubmitModalFormFields = () => {
  const { values } = useFormikContext();

  return (
    <Form.Field>
      <RadioField
        control={Checkbox}
        fieldPath="acceptTermsOfService"
        label={<Trans defaults={msgWarningTos} components={{ link: <b /> }} />}
        checked={_get(values, "acceptTermsOfService") === true}
        onChange={({ data, formikProps }) => {
          formikProps.form.setFieldValue("acceptTermsOfService", data.checked);
        }}
        optimized
      />
      <ErrorLabel
        role="alert"
        fieldPath="acceptTermsOfService"
        className="mt-0 mb-5"
      />
    </Form.Field>
  );
};

export const parameters = {
  confirmSubmitReviewSchema: Yup.object({
    acceptTermsOfService: Yup.bool().oneOf(
      [true],
      i18next.t("You must accept this.")
    ),
  }),
  formikDefaults: {
    acceptTermsOfService: false,
  },
};

export const SubmitReviewModalFormFields = parametrize(
  SubmitReviewModal,
  parameters
);
