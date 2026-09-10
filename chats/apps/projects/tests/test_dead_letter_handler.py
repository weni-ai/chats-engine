from unittest.mock import Mock

from django.test import TestCase, override_settings

from chats.apps.projects.usecases.dead_letter_handler import DeadLetterHandler
from chats.apps.projects.usecases.exceptions import (
    InvalidDLQHeaders,
    ReceivedErrorMessage,
)


class TestDeadLetterHandler(TestCase):
    def _make_message(self, headers=None):
        message = Mock()
        message.headers = headers if headers is not None else {}
        return message

    def test_execute_raises_received_error_message_when_error_type_present(self):
        message = self._make_message()
        content = {
            "error_type": "ValueError",
            "error_message": "bad payload",
            "original_message": {"foo": "bar"},
        }
        handler = DeadLetterHandler(message=message, dead_letter_content=content)

        with self.assertRaises(ReceivedErrorMessage) as ctx:
            handler.execute()

        message_text = str(ctx.exception)
        self.assertIn("ValueError", message_text)
        self.assertIn("bad payload", message_text)
        self.assertIn("foo", message_text)

    def test_execute_raises_invalid_dlq_headers_when_no_x_death(self):
        message = self._make_message(headers={})
        handler = DeadLetterHandler(message=message, dead_letter_content={})

        with self.assertRaises(InvalidDLQHeaders) as ctx:
            handler.execute()

        self.assertIn("x-death", str(ctx.exception))

    def test_execute_raises_when_reason_in_reject_reason(self):
        message = self._make_message(
            headers={"x-death": [{"reason": "rejected", "count": 1}]}
        )
        handler = DeadLetterHandler(message=message, dead_letter_content={})

        with self.assertRaises(InvalidDLQHeaders) as ctx:
            handler.execute()

        self.assertIn("rejected", str(ctx.exception))

    def test_execute_raises_when_reason_is_delivery_limit(self):
        message = self._make_message(
            headers={"x-death": [{"reason": "delivery_limit", "count": 1}]}
        )
        handler = DeadLetterHandler(message=message, dead_letter_content={})

        with self.assertRaises(InvalidDLQHeaders) as ctx:
            handler.execute()

        self.assertIn("delivery_limit", str(ctx.exception))

    @override_settings(EDA_REQUEUE_LIMIT=2)
    def test_execute_raises_when_count_exceeds_requeue_limit(self):
        message = self._make_message(
            headers={"x-death": [{"reason": "expired", "count": 2}]}
        )
        handler = DeadLetterHandler(message=message, dead_letter_content={})

        with self.assertRaises(InvalidDLQHeaders) as ctx:
            handler.execute()

        self.assertIn("2", str(ctx.exception))

    @override_settings(EDA_REQUEUE_LIMIT=5)
    def test_execute_passes_when_under_requeue_limit(self):
        message = self._make_message(
            headers={"x-death": [{"reason": "expired", "count": 1}]}
        )
        handler = DeadLetterHandler(message=message, dead_letter_content={})

        self.assertIsNone(handler.execute())

    def test_execute_uses_first_x_death_entry(self):
        message = self._make_message(
            headers={
                "x-death": [
                    {"reason": "rejected", "count": 1},
                    {"reason": "expired", "count": 0},
                ]
            }
        )
        handler = DeadLetterHandler(message=message, dead_letter_content={})

        with self.assertRaises(InvalidDLQHeaders):
            handler.execute()
