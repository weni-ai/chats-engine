from unittest.mock import MagicMock

from django.test import SimpleTestCase, override_settings

from chats.apps.projects.usecases.dead_letter_handler import DeadLetterHandler
from chats.apps.projects.usecases.exceptions import (
    InvalidDLQHeaders,
    ReceivedErrorMessage,
)


class DeadLetterHandlerTests(SimpleTestCase):
    def _handler(self, content=None, headers=None):
        message = MagicMock()
        message.headers = headers or {}
        return DeadLetterHandler(message, content or {})

    def test_raises_when_error_type_is_present(self):
        handler = self._handler(
            content={
                "error_type": "ValidationError",
                "error_message": "bad payload",
                "original_message": {"id": 1},
            }
        )

        with self.assertRaises(ReceivedErrorMessage) as context:
            handler.execute()

        self.assertIn("ValidationError", str(context.exception))
        self.assertIn("bad payload", str(context.exception))

    def test_raises_when_x_death_header_is_missing(self):
        handler = self._handler(headers={})

        with self.assertRaises(InvalidDLQHeaders) as context:
            handler.execute()

        self.assertIn("x-death", str(context.exception))

    def test_raises_for_rejected_reason(self):
        handler = self._handler(
            headers={"x-death": [{"reason": "rejected", "count": 1}]}
        )

        with self.assertRaises(InvalidDLQHeaders) as context:
            handler.execute()

        self.assertIn("rejected", str(context.exception))

    def test_raises_for_delivery_limit_reason(self):
        handler = self._handler(
            headers={"x-death": [{"reason": "delivery_limit", "count": 1}]}
        )

        with self.assertRaises(InvalidDLQHeaders):
            handler.execute()

    @override_settings(EDA_REQUEUE_LIMIT=3)
    def test_raises_when_requeue_limit_is_reached(self):
        handler = self._handler(
            headers={"x-death": [{"reason": "expired", "count": 3}]}
        )

        with self.assertRaises(InvalidDLQHeaders) as context:
            handler.execute()

        self.assertIn("3 times", str(context.exception))

    @override_settings(EDA_REQUEUE_LIMIT=5)
    def test_allows_requeue_when_reason_and_count_are_valid(self):
        handler = self._handler(
            headers={"x-death": [{"reason": "expired", "count": 2}]}
        )

        self.assertIsNone(handler.execute())
