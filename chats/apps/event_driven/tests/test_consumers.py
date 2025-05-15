from unittest import TestCase, mock
import json

from chats.apps.projects.consumers.dead_letter_consumer import DeadLetterConsumer
from chats.apps.event_driven.consumers import pyamqp_call_dlx_when_error, EDAConsumer
from chats.apps.event_driven.signals import message_started, message_finished

class TestEDAConsumer(TestCase):
    def setUp(self):
        self.mock_message = mock.Mock(spec=amqp.Message)
        self.mock_message.channel = mock.Mock()
        self.mock_message.delivery_tag = "test_delivery_tag"
        self.mock_message.body = b'{"test": "data"}'
        self.mock_message.headers = {}

    def test_handle_sends_signals(self):
        """
        Tests if message_started and message_finished signals are sent
        """
        message_started_mock = mock.Mock()
        message_finished_mock = mock.Mock()
        message_started.connect(message_started_mock)
        message_finished.connect(message_finished_mock)

        class TestConsumer(EDAConsumer):
            def consume(self, message):
                pass

        consumer = TestConsumer()
        consumer.handle(self.mock_message)

        message_started_mock.assert_called_once()
        message_finished_mock.assert_called_once()

        message_started.disconnect(message_started_mock)
        message_finished.disconnect(message_finished_mock)

    def test_handle_calls_consume(self):
        """
        Tests if the consume method is called
        """
        class TestConsumer(EDAConsumer):
            def consume(self, message):
                self.consume_called = True

        consumer = TestConsumer()
        consumer.handle(self.mock_message)

        self.assertTrue(consumer.consume_called)


class TestPyamqpCallDlxWhenError(TestCase):
    def setUp(self):
        self.mock_message = mock.Mock(spec=amqp.Message)
        self.mock_message.channel = mock.Mock()
        self.mock_message.delivery_tag = "test_delivery_tag"
        self.mock_message.body = b'{"test": "data"}'
        self.mock_message.headers = {}

    def test_decorator_success(self):
        """
        Tests the decorator when there is no error
        """
        @pyamqp_call_dlx_when_error(
            routing_key="test",
            default_exchange="test_exchange",
            consumer_name="test_consumer"
        )
        def test_consumer(message):
            return "success"

        result = test_consumer(self.mock_message)
        
        self.assertEqual(result, "success")
        self.mock_message.channel.basic_reject.assert_not_called()

    def test_decorator_error(self):
        """
        Tests the decorator when there is an error
        """
        @pyamqp_call_dlx_when_error(
            routing_key="test",
            default_exchange="test_exchange",
            consumer_name="test_consumer"
        )
        def test_consumer(message):
            raise Exception("test error")

        test_consumer(self.mock_message)
        
        self.mock_message.channel.basic_reject.assert_called_once_with(
            "test_delivery_tag", requeue=False
        )

    def test_decorator_error_with_callback_exchange(self):
        """
        Tests the decorator when there is an error and there is a callback exchange
        """
        self.mock_message.headers = {"callback_exchange": "custom_exchange"}
        
        @pyamqp_call_dlx_when_error(
            routing_key="test",
            default_exchange="test_exchange",
            consumer_name="test_consumer"
        )
        def test_consumer(message):
            raise Exception("test error")

        test_consumer(self.mock_message)
        
        self.mock_message.channel.basic_reject.assert_called_once_with(
            "test_delivery_tag", requeue=False
        )

class TestDeadLetterConsumer(TestCase):
    def setUp(self):
        self.mock_message = mock.Mock(spec=amqp.Message)
        self.mock_message.channel = mock.Mock()
        self.mock_message.delivery_tag = "test_delivery_tag"
        self.mock_message.body = json.dumps({"test": "data"}).encode()
        self.mock_message.headers = {
            "x-first-death-queue": "test_queue"
        }

    @mock.patch('chats.apps.projects.consumers.dead_letter_consumer.DeadLetterHandler')
    @mock.patch('chats.apps.projects.consumers.dead_letter_consumer.basic_publish')
    def test_consume_success(self, mock_basic_publish, mock_handler):
        """
        Tests successful message consumption
        """
        mock_handler_instance = mock.Mock()
        mock_handler.return_value = mock_handler_instance

        DeadLetterConsumer.consume(self.mock_message)

        mock_handler.assert_called_once_with(
            message=self.mock_message,
            dead_letter_content={"test": "data"}
        )
        mock_handler_instance.execute.assert_called_once()

        mock_basic_publish.assert_called_once_with(
            channel=self.mock_message.channel,
            content={"test": "data"},
            exchange="",
            routing_key="test_queue",
            headers=self.mock_message.headers
        )

        self.mock_message.channel.basic_ack.assert_called_once_with("test_delivery_tag")
        self.mock_message.channel.basic_reject.assert_not_called()

    @mock.patch('chats.apps.projects.consumers.dead_letter_consumer.DeadLetterHandler')
    @mock.patch('chats.apps.projects.consumers.dead_letter_consumer.basic_publish')
    def test_consume_handler_error(self, mock_basic_publish, mock_handler):
        """
        Tests behavior when handler raises an exception
        """
        mock_handler_instance = mock.Mock()
        mock_handler_instance.execute.side_effect = Exception("Handler error")
        mock_handler.return_value = mock_handler_instance

        DeadLetterConsumer.consume(self.mock_message)

        mock_handler.assert_called_once_with(
            message=self.mock_message,
            dead_letter_content={"test": "data"}
        )

        self.mock_message.channel.basic_reject.assert_called_once_with(
            "test_delivery_tag", requeue=False
        )
        self.mock_message.channel.basic_ack.assert_not_called()

        mock_basic_publish.assert_not_called()

    @mock.patch('chats.apps.projects.consumers.dead_letter_consumer.DeadLetterHandler')
    @mock.patch('chats.apps.projects.consumers.dead_letter_consumer.basic_publish')
    def test_consume_invalid_json(self, mock_basic_publish, mock_handler):
        """
        Tests behavior when JSON is invalid
        """
        self.mock_message.body = b'invalid json'

        DeadLetterConsumer.consume(self.mock_message)

        mock_handler.assert_not_called()

        self.mock_message.channel.basic_reject.assert_called_once_with(
            "test_delivery_tag", requeue=False
        )
        self.mock_message.channel.basic_ack.assert_not_called()

        mock_basic_publish.assert_not_called()

    @mock.patch('chats.apps.projects.consumers.dead_letter_consumer.DeadLetterHandler')
    @mock.patch('chats.apps.projects.consumers.dead_letter_consumer.basic_publish')
    def test_consume_missing_queue_header(self, mock_basic_publish, mock_handler):
        """
        Tests behavior when the x-first-death-queue header is missing
        """
        self.mock_message.headers = {}

        mock_handler_instance = mock.Mock()
        mock_handler.return_value = mock_handler_instance

        DeadLetterConsumer.consume(self.mock_message)

        mock_handler.assert_called_once_with(
            message=self.mock_message,
            dead_letter_content={"test": "data"}
        )

        mock_basic_publish.assert_called_once_with(
            channel=self.mock_message.channel,
            content={"test": "data"},
            exchange="",
            routing_key=None,
            headers={}
        )

        self.mock_message.channel.basic_ack.assert_called_once_with("test_delivery_tag")
        self.mock_message.channel.basic_reject.assert_not_called()