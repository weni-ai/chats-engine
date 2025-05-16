from unittest import mock
from django.test import SimpleTestCase

from chats.apps.api.v1.internal.eda_clients.billing_client import RoomsInfoMixin
from chats.apps.api.v1.internal.eda_clients.flows_eda_client import (
    FlowsQueueMixin,
    FlowsTicketerMixin,
)


class DummyMixin(RoomsInfoMixin):
    """Concrete implementation for testing purposes."""

    def __init__(self):
        pass


class DummyQueueMixin(FlowsQueueMixin):
    def __init__(self):
        pass


class DummyTicketerMixin(FlowsTicketerMixin):
    def __init__(self):
        pass


class RoomsInfoMixinTests(SimpleTestCase):
    @mock.patch("chats.apps.api.v1.internal.eda_clients.billing_client.EventDrivenAPP")
    def test_request_room_publishes_message(self, mock_app):
        # Arrange
        instance = DummyMixin()
        backend = mock_app.return_value.backend

        # Act
        instance.request_room({"foo": "bar"})

        # Assert
        backend.basic_publish.assert_called_once_with(
            content={"foo": "bar"},
            exchange=instance.base_room_exchange,
            headers={"callback_exchange": mock.ANY},
        )


class FlowsQueueMixinTests(SimpleTestCase):
    @mock.patch("chats.apps.api.v1.internal.eda_clients.flows_eda_client.EventDrivenAPP")
    def test_request_queue_publishes_message(self, mock_app):
        # Arrange
        mixin = DummyQueueMixin()
        backend = mock_app.return_value.backend

        # Act
        mixin.request_queue("create", {"a": 1})

        # Assert
        backend.basic_publish.assert_called_once_with(
            content={"a": 1},
            exchange=mixin.base_queue_exchange,
            headers={"callback_exchange": mock.ANY},
        )


class FlowsTicketerMixinTests(SimpleTestCase):
    @mock.patch("chats.apps.api.v1.internal.eda_clients.flows_eda_client.EventDrivenAPP")
    def test_request_ticketer_publishes_message(self, mock_app):
        # Arrange
        mixin = DummyTicketerMixin()
        backend = mock_app.return_value.backend

        # Act
        mixin.request_ticketer({"b": 2})

        # Assert
        backend.basic_publish.assert_called_once_with(
            content={"b": 2},
            exchange=mixin.base_ticketer_exchange,
            headers={"callback_exchange": mock.ANY},
        ) 