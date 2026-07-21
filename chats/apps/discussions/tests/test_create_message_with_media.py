from unittest.mock import patch

from django.test import TestCase

from chats.apps.accounts.models import User
from chats.apps.contacts.models import Contact
from chats.apps.discussions.models import Discussion, DiscussionMessage
from chats.apps.discussions.usecases.create_message_with_media import (
    CreateMessageWithMediaUseCase,
)
from chats.apps.projects.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


class TestCreateMessageWithMediaUseCase(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Disc Project")
        self.sector = Sector.objects.create(
            name="Disc Sector",
            project=self.project,
            rooms_limit=2,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Disc Queue", sector=self.sector)
        self.contact = Contact.objects.create(name="Disc Contact")
        self.user = User.objects.create(email="disc@test.com")
        self.room = Room.objects.create(queue=self.queue, contact=self.contact)
        self.discussion = Discussion.objects.create(
            subject="Subject",
            created_by=self.user,
            room=self.room,
            queue=self.queue,
        )

    @patch.object(DiscussionMessage, "notify")
    def test_execute_creates_message_with_media_and_notifies(self, mock_notify):
        usecase = CreateMessageWithMediaUseCase(
            discussion=self.discussion,
            user=self.user,
            msg_content={
                "text": "see this",
                "content_type": "image/png",
            },
        )

        media = usecase.execute()

        self.assertIsNotNone(media)
        self.assertEqual(media.content_type, "image/png")
        msg = DiscussionMessage.objects.get(pk=media.message.pk)
        self.assertEqual(msg.text, "see this")
        self.assertEqual(msg.discussion, self.discussion)
        self.assertEqual(msg.user, self.user)
        mock_notify.assert_called_once_with("create")

    @patch.object(DiscussionMessage, "notify")
    def test_execute_skips_notify_when_disabled(self, mock_notify):
        usecase = CreateMessageWithMediaUseCase(
            discussion=self.discussion,
            user=self.user,
            msg_content={
                "text": "",
                "content_type": "text/plain",
            },
            notify=False,
        )

        media = usecase.execute()

        self.assertIsNotNone(media)
        mock_notify.assert_not_called()

    @patch.object(DiscussionMessage, "notify")
    def test_execute_defaults_text_to_empty_string(self, mock_notify):
        usecase = CreateMessageWithMediaUseCase(
            discussion=self.discussion,
            user=self.user,
            msg_content={"content_type": "image/jpeg"},
        )

        media = usecase.execute()

        msg = DiscussionMessage.objects.get(pk=media.message.pk)
        self.assertEqual(msg.text, "")
