from datetime import time
from unittest.mock import MagicMock, patch

from django.core import mail
from django.test import TestCase

from chats.apps.accounts.models import User
from chats.apps.contacts.models import Contact
from chats.apps.projects.models.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.rooms.usecases.send_room_export_email import SendRoomExportEmail
from chats.apps.sectors.models import Sector


class SendRoomExportEmailTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="agent@example.com")
        self.project = Project.objects.create(name="Project")
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=10,
            work_start=time(hour=0),
            work_end=time(hour=23, minute=59),
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)
        self.contact = Contact.objects.create(external_id="contact-1", name="Contact")
        self.room = Room.objects.create(
            contact=self.contact, queue=self.queue, user=self.user
        )

        self.storage = MagicMock()
        self.storage.save.side_effect = lambda name, content: name
        self.storage.get_download_url.side_effect = (
            lambda path, expiration: f"https://example.com/{path}"
        )

    def test_uploads_each_file_and_returns_download_urls(self):
        usecase = SendRoomExportEmail(storage=self.storage)

        download_urls = usecase.execute(
            room=self.room,
            files={"html": b"<html/>", "pdf": b"%PDF"},
            recipient_email="user@example.com",
        )

        self.assertEqual(set(download_urls.keys()), {"html", "pdf"})
        self.assertEqual(self.storage.save.call_count, 2)
        for ext, url in download_urls.items():
            self.assertIn(str(self.room.uuid), url)
            self.assertTrue(url.endswith(f".{ext}"))

    def test_sends_one_email_per_generated_file(self):
        usecase = SendRoomExportEmail(storage=self.storage)

        usecase.execute(
            room=self.room,
            files={"html": b"<html/>", "pdf": b"%PDF"},
            recipient_email="user@example.com",
        )

        self.assertEqual(len(mail.outbox), 2)
        bodies = [m.body for m in mail.outbox]
        self.assertTrue(any("https://example.com/" in body for body in bodies))
        # Each message should be addressed to the requester
        for message in mail.outbox:
            self.assertIn("user@example.com", message.to)

    def test_email_body_contains_project_name_instead_of_room_uuid(self):
        usecase = SendRoomExportEmail(storage=self.storage)

        usecase.execute(
            room=self.room,
            files={"html": b"<html/>"},
            recipient_email="user@example.com",
        )

        message = mail.outbox[0]
        html_alt = next(
            (content for content, mimetype in message.alternatives if mimetype == "text/html"),
            "",
        )
        self.assertIn(self.project.name, message.body)
        self.assertIn(
            f"The chat export for the {self.project.name} project is ready",
            html_alt,
        )

    def test_failure_email_body_contains_project_name(self):
        usecase = SendRoomExportEmail(storage=self.storage)

        usecase.send_failure_notification(
            room=self.room,
            recipient_email="user@example.com",
            error_message="boom",
        )

        message = mail.outbox[0]
        html_alt = next(
            (content for content, mimetype in message.alternatives if mimetype == "text/html"),
            "",
        )
        self.assertIn(self.project.name, message.body)
        self.assertIn(
            f"Unable to generate chat export for the {self.project.name} project.",
            html_alt,
        )

    def test_sends_single_email_when_only_one_format_requested(self):
        usecase = SendRoomExportEmail(storage=self.storage)

        usecase.execute(
            room=self.room,
            files={"html": b"<html/>"},
            recipient_email="user@example.com",
        )

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("https://example.com/", mail.outbox[0].body)

    def test_raises_when_no_files_are_provided(self):
        usecase = SendRoomExportEmail(storage=self.storage)

        with self.assertRaises(ValueError):
            usecase.execute(
                room=self.room,
                files={},
                recipient_email="user@example.com",
            )

    def test_failure_notification_sends_email_with_error_message(self):
        usecase = SendRoomExportEmail(storage=self.storage)

        usecase.send_failure_notification(
            room=self.room,
            recipient_email="user@example.com",
            error_message="something went wrong",
        )

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertIn("user@example.com", message.to)
        self.assertIn("something went wrong", message.body)

    def test_uses_protocol_as_identifier_when_available(self):
        Room.objects.filter(pk=self.room.pk).update(protocol="PROTO-42")
        self.room.refresh_from_db()
        usecase = SendRoomExportEmail(storage=self.storage)

        usecase.execute(
            room=self.room,
            files={"html": b"<html/>"},
            recipient_email="user@example.com",
        )

        message = mail.outbox[0]
        self.assertIn("PROTO-42", message.subject)

    def test_does_not_send_emails_when_an_upload_fails(self):
        # Second upload fails: no email should be sent for the first one either,
        # so retries don't end up duplicating delivery.
        self.storage.save.side_effect = [
            "first-file.html",
            RuntimeError("s3 down"),
        ]

        usecase = SendRoomExportEmail(storage=self.storage)

        with self.assertRaises(RuntimeError):
            usecase.execute(
                room=self.room,
                files={"html": b"<html/>", "pdf": b"%PDF"},
                recipient_email="user@example.com",
            )

        self.assertEqual(len(mail.outbox), 0)

    @patch("chats.apps.rooms.usecases.send_room_export_email.RoomExportStorage")
    def test_uses_default_storage_when_none_provided(self, storage_cls):
        instance = MagicMock()
        instance.save.side_effect = lambda name, content: name
        instance.get_download_url.side_effect = (
            lambda path, expiration: f"https://x/{path}"
        )
        storage_cls.return_value = instance

        usecase = SendRoomExportEmail()
        usecase.execute(
            room=self.room,
            files={"html": b"<html/>"},
            recipient_email="user@example.com",
        )

        storage_cls.assert_called_once()
        instance.save.assert_called_once()
