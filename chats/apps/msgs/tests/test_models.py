from django.test import TestCase
from django.utils import timezone
from django.utils.timezone import timedelta

from chats.apps.msgs.models import Message, MessageMedia
from chats.apps.rooms.models import Room


class TestMessageModel(TestCase):
    def setUp(self):
        self.room = Room.objects.create()

    def test_create_message_passing_created_on(self):
        timestamp = timezone.now() - timedelta(days=2)

        msg = Message.objects.create(room=self.room, created_on=timestamp)

        self.assertEqual(msg.created_on.date(), timestamp.date())
        self.assertEqual(msg.created_on.hour, timestamp.hour)
        self.assertEqual(msg.created_on.minute, timestamp.minute)
        self.assertEqual(msg.created_on.second, timestamp.second)

    def test_create_message_without_passing_created_on(self):
        msg = Message.objects.create(room=self.room)

        self.assertEqual(msg.created_on.date(), timezone.now().date())


class TestMessageMediaModel(TestCase):
    def setUp(self):
        self.room = Room.objects.create()
        self.msg = Message.objects.create(room=self.room)

    def test_create_message_media_passing_created_on(self):
        timestamp = timezone.now() - timedelta(days=2)

        msg_media = MessageMedia.objects.create(message=self.msg, created_on=timestamp)

        self.assertEqual(msg_media.created_on.date(), timestamp.date())
        self.assertEqual(msg_media.created_on.hour, timestamp.hour)
        self.assertEqual(msg_media.created_on.minute, timestamp.minute)
        self.assertEqual(msg_media.created_on.second, timestamp.second)

    def test_create_message_media_without_passing_created_on(self):
        msg_media = MessageMedia.objects.create(message=self.msg)

        self.assertEqual(msg_media.created_on.date(), timezone.now().date())
