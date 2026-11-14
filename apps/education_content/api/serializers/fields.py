import json

from rest_framework import serializers


class MultipartJSONListField(serializers.Field):
    """
    Parses a JSON array received as a multipart/form-data field
    and validates each item using the provided serializer.
    """

    default_error_messages = {
        "invalid_json": "Invalid JSON format.",
        "not_a_list": "Expected a JSON array.",
    }

    def __init__(self, serializer_class, **kwargs):
        self.serializer_class = serializer_class
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except (json.JSONDecodeError, TypeError):
                self.fail("invalid_json")

        if not isinstance(data, list):
            self.fail("not_a_list")

        serializer = self.serializer_class(
            data=data,
            many=True,
            context=self.context,
        )

        serializer.is_valid(raise_exception=True)

        return serializer.validated_data

    def to_representation(self, value):
        if hasattr(value, "all"):
            value = value.all()

        serializer = self.serializer_class(
            instance=value,
            many=True,
            context=self.context,
        )

        return serializer.data
