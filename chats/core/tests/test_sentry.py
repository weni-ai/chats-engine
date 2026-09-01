from django.core.exceptions import ValidationError as DjangoValidationError
from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError as DRFValidationError

from chats.core.sentry import (
    is_closed_websocket_error,
    is_expected_validation_error,
    sentry_before_send,
)


class TestSentryBeforeSend(SimpleTestCase):
    def test_drops_closed_protocol_message(self):
        event = {"message": "Attempt to send on a closed protocol"}
        self.assertIsNone(sentry_before_send(event, {}))

    def test_drops_disconnected_exception(self):
        class Disconnected(Exception):
            pass

        event = {"message": "ws error"}
        hint = {"exc_info": (Disconnected, Disconnected("closed"), None)}
        self.assertIsNone(sentry_before_send(event, hint))

    def test_drops_expected_validation_error(self):
        exc = DRFValidationError(
            {"detail": "Closed rooms can't receive messages"}
        )
        event = {"message": str(exc)}
        hint = {"exc_info": (DRFValidationError, exc, None)}
        self.assertIsNone(sentry_before_send(event, hint))

    def test_drops_worker_lost_sigterm(self):
        class WorkerLostError(Exception):
            pass

        exc = WorkerLostError(
            "Worker exited prematurely: signal 15 (SIGTERM) Job: 1."
        )
        event = {"message": str(exc)}
        hint = {"exc_info": (WorkerLostError, exc, None)}
        self.assertIsNone(sentry_before_send(event, hint))

    def test_drops_bedrock_service_unavailable(self):
        event = {
            "message": (
                "An error occurred (ServiceUnavailableException) when calling "
                "the InvokeModel operation"
            )
        }
        self.assertIsNone(sentry_before_send(event, {}))

    def test_drops_growthbook_and_keycloak_noise(self):
        self.assertIsNone(
            sentry_before_send(
                {"message": "Error getting feature flags definitions from GrowthBook"},
                {},
            )
        )
        self.assertIsNone(
            sentry_before_send(
                {
                    "message": (
                        "HTTPSConnectionPool(host='accounts.weni.ai', port=443): "
                        "Max retries exceeded"
                    )
                },
                {},
            )
        )

    def test_keeps_real_bugs(self):
        event = {"message": "'NoneType' object has no attribute 'project'"}
        self.assertEqual(sentry_before_send(event, {}), event)

        exc = AttributeError("'NoneType' object has no attribute 'project'")
        hint = {"exc_info": (AttributeError, exc, None)}
        self.assertEqual(
            sentry_before_send({"message": str(exc)}, hint),
            {"message": str(exc)},
        )


class TestSentryHelpers(SimpleTestCase):
    def test_is_closed_websocket_error(self):
        self.assertTrue(
            is_closed_websocket_error(RuntimeError("Attempt to send on a closed protocol"))
        )
        self.assertFalse(is_closed_websocket_error(RuntimeError("other")))

    def test_is_expected_validation_error(self):
        self.assertTrue(
            is_expected_validation_error(
                DRFValidationError({"detail": "Closed rooms can't receive messages"})
            )
        )
        self.assertTrue(
            is_expected_validation_error(
                DjangoValidationError(
                    "you can't have more than one active status per project."
                )
            )
        )
        self.assertFalse(
            is_expected_validation_error(DRFValidationError({"detail": "other"}))
        )
