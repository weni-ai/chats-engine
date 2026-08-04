from django.test import TestCase
from rest_framework import serializers

from chats.apps.api.core.serializers import CommaSeparatedListField


class CommaSeparatedListFieldTests(TestCase):
    def setUp(self):
        self.field = CommaSeparatedListField(child=serializers.CharField())

    def test_none_returns_empty_list(self):
        self.assertEqual(self.field.to_internal_value(None), [])

    def test_empty_string_returns_empty_list(self):
        self.assertEqual(self.field.to_internal_value(""), [])

    def test_comma_separated_string(self):
        self.assertEqual(
            self.field.to_internal_value("waiting,ongoing"),
            ["waiting", "ongoing"],
        )

    def test_strips_whitespace_around_tokens(self):
        self.assertEqual(
            self.field.to_internal_value(" waiting , ongoing "),
            ["waiting", "ongoing"],
        )

    def test_ignores_empty_tokens(self):
        self.assertEqual(
            self.field.to_internal_value("waiting,,ongoing,"),
            ["waiting", "ongoing"],
        )

    def test_list_with_comma_separated_string(self):
        self.assertEqual(
            self.field.to_internal_value(["waiting,ongoing"]),
            ["waiting", "ongoing"],
        )

    def test_list_of_values(self):
        self.assertEqual(
            self.field.to_internal_value(["waiting", "ongoing"]),
            ["waiting", "ongoing"],
        )

    def test_list_with_empty_and_whitespace_items(self):
        self.assertEqual(
            self.field.to_internal_value(["", "  ", "waiting"]),
            ["waiting"],
        )

    def test_uuid_child_validates_each_item(self):
        field = CommaSeparatedListField(child=serializers.UUIDField())
        uuid_a = "11111111-1111-1111-1111-111111111111"
        uuid_b = "22222222-2222-2222-2222-222222222222"

        result = field.to_internal_value(f"{uuid_a},{uuid_b}")

        self.assertEqual([str(value) for value in result], [uuid_a, uuid_b])

    def test_invalid_child_value_raises_validation_error(self):
        field = CommaSeparatedListField(child=serializers.UUIDField())

        with self.assertRaises(serializers.ValidationError):
            field.to_internal_value("not-a-uuid")
