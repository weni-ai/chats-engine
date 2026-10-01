from django.test import SimpleTestCase

from chats.apps.rooms.email_templates import (
    get_room_export_failed_email,
    get_room_export_ready_email,
)


class RoomExportEmailTemplatesTests(SimpleTestCase):
    def test_ready_email_contains_project_and_url(self):
        plain, html = get_room_export_ready_email(
            "Acme", "https://cdn.example/file.zip"
        )

        self.assertIn("Acme", plain)
        self.assertIn("https://cdn.example/file.zip", plain)
        self.assertIn("Acme", html)
        self.assertIn("https://cdn.example/file.zip", html)

    def test_failed_email_uses_unknown_error_fallback(self):
        plain, html = get_room_export_failed_email("Acme")

        self.assertIn("Acme", plain)
        self.assertIn("Unknown error", plain)
        self.assertIn("Acme", html)

    def test_failed_email_includes_error_message(self):
        plain, _html = get_room_export_failed_email("Acme", error_message="timeout")

        self.assertIn("timeout", plain)
