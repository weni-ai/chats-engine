from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError

from chats.apps.msgs.exceptions import MessageCreateError
from chats.apps.msgs.validators.agent_message_create import (
    first_serializer_error,
    map_save_validation_error,
)


class FirstSerializerErrorTests(SimpleTestCase):
    def test_returns_first_list_message_from_dict(self):
        self.assertEqual(
            first_serializer_error({"text": ["This field is required."]}),
            "This field is required.",
        )

    def test_returns_nested_dict_message(self):
        errors = {"media": {"url": ["Invalid URL"]}}
        self.assertEqual(first_serializer_error(errors), "Invalid URL")

    def test_returns_non_list_scalar_value(self):
        self.assertEqual(first_serializer_error({"detail": "Forbidden"}), "Forbidden")

    def test_returns_first_item_from_list(self):
        self.assertEqual(first_serializer_error(["first", "second"]), "first")

    def test_returns_string_representation_for_empty_errors(self):
        self.assertEqual(first_serializer_error({}), str({}))


class MapSaveValidationErrorTests(SimpleTestCase):
    def test_maps_closed_room_error(self):
        error = ValidationError("Closed rooms can't receive messages")

        mapped = map_save_validation_error(error)

        self.assertIsInstance(mapped, MessageCreateError)
        self.assertEqual(mapped.error_code, "room_closed")

    def test_maps_message_window_expired_error(self):
        error = ValidationError("Message outside the 24h window")

        mapped = map_save_validation_error(error)

        self.assertEqual(mapped.error_code, "message_window_expired")

    def test_maps_generic_validation_error_with_details(self):
        detail = {"text": ["Required"]}
        error = ValidationError(detail)

        mapped = map_save_validation_error(error)

        self.assertEqual(mapped.error_code, "validation_error")
        self.assertEqual(mapped.details, detail)
