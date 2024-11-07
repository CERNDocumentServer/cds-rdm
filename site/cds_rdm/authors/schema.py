from invenio_records_resources.services.records.schema import BaseRecordSchema
from marshmallow import fields


class AuthorSchema(BaseRecordSchema):
    """Author schema."""

    given_name = fields.Str(required=True)
    family_name = fields.Str(required=True)
    affiliations = fields.Str()
    user_id = fields.Str()
