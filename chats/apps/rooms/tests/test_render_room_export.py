import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from django.test import TestCase

from chats.apps.rooms.usecases.render_room_export import (
    FORMAT_HTML,
    FORMAT_PDF,
    RenderRoomExport,
    UnsupportedExportFormatError,
)

try:
    import weasyprint  # noqa: F401

    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False


def _build_sample_data() -> dict:
    started = datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc)
    ended = datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)
    return {
        "meta": {
            "generated_at": started,
            "generated_by": "agent@example.com",
        },
        "room": {
            "uuid": "room-uuid",
            "protocol": "PROTO-123",
            "started_at": started,
            "ended_at": ended,
            "ended_by": "agent@example.com",
            "tags": ["urgent", "vip"],
            "custom_fields": {"motivo": "duvida", "prioridade": "alta"},
        },
        "contact": {
            "name": "Test Contact",
            "email": "contact@example.com",
            "phone": "+5511999999999",
            "external_id": "ext-1",
            "custom_fields": {"cpf": "000.000.000-00"},
        },
        "agents": [
            {"email": "agent@example.com", "name": "Agent A", "is_current": True},
            {"email": "other@example.com", "name": "Agent B", "is_current": False},
        ],
        "timeline": [
            {
                "type": "message",
                "sender_type": "contact",
                "sender_name": "Test Contact",
                "created_on": started,
                "text": "Hello world",
                "medias": [],
            },
            {
                "type": "message",
                "sender_type": "agent",
                "sender_name": "Agent A",
                "created_on": started,
                "text": "Hi there",
                "medias": [
                    {
                        "content_type": "image/jpeg",
                        "url": "https://example.com/img.jpg",
                        "data_uri": "data:image/jpeg;base64,FAKE",
                    }
                ],
            },
            {
                "type": "internal_note",
                "sender_name": "Agent A",
                "created_on": started,
                "text": "Internal observation",
                "anchored_message_uuid": None,
            },
            {
                "type": "transfer_chip",
                "kind": "pick",
                "from": {"type": "queue", "name": "Support"},
                "to": {"type": "user", "name": "Agent A"},
                "by": {"type": "user", "name": "Agent A"},
                "created_on": started,
            },
        ],
    }


class RenderRoomExportHtmlTests(TestCase):
    def setUp(self):
        self.data = _build_sample_data()
        self.usecase = RenderRoomExport()

    def test_returns_html_as_bytes(self):
        result = self.usecase.execute(self.data, [FORMAT_HTML])

        self.assertIn(FORMAT_HTML, result)
        self.assertIsInstance(result[FORMAT_HTML], bytes)

    def test_html_contains_room_protocol(self):
        result = self.usecase.execute(self.data, [FORMAT_HTML])
        html = result[FORMAT_HTML].decode("utf-8")
        self.assertIn("PROTO-123", html)

    def test_html_contains_contact_name(self):
        result = self.usecase.execute(self.data, [FORMAT_HTML])
        html = result[FORMAT_HTML].decode("utf-8")
        self.assertIn("Test Contact", html)

    def test_html_contains_timeline_messages(self):
        result = self.usecase.execute(self.data, [FORMAT_HTML])
        html = result[FORMAT_HTML].decode("utf-8")
        self.assertIn("Hello world", html)
        self.assertIn("Hi there", html)

    def test_html_contains_internal_note(self):
        result = self.usecase.execute(self.data, [FORMAT_HTML])
        html = result[FORMAT_HTML].decode("utf-8")
        self.assertIn("Internal observation", html)

    def test_html_contains_transfer_chip_text(self):
        result = self.usecase.execute(self.data, [FORMAT_HTML])
        html = result[FORMAT_HTML].decode("utf-8")
        self.assertIn("Agent A", html)

    def test_html_lists_all_agents(self):
        result = self.usecase.execute(self.data, [FORMAT_HTML])
        html = result[FORMAT_HTML].decode("utf-8")
        self.assertIn("agent@example.com", html)
        self.assertIn("other@example.com", html)

    def test_html_uses_data_uri_when_available(self):
        result = self.usecase.execute(self.data, [FORMAT_HTML])
        html = result[FORMAT_HTML].decode("utf-8")
        # embed_media=True in HTML branch, template prefers data_uri
        self.assertIn("data:image/jpeg;base64,FAKE", html)

    def test_html_renders_meta_generated_by(self):
        result = self.usecase.execute(self.data, [FORMAT_HTML])
        html = result[FORMAT_HTML].decode("utf-8")
        self.assertIn("agent@example.com", html)

    def test_html_renders_tags(self):
        result = self.usecase.execute(self.data, [FORMAT_HTML])
        html = result[FORMAT_HTML].decode("utf-8")
        self.assertIn("urgent", html)


class RenderRoomExportPdfTests(TestCase):
    def setUp(self):
        self.data = _build_sample_data()
        self.usecase = RenderRoomExport()

    @patch("weasyprint.HTML")
    def test_pdf_calls_weasyprint_with_rendered_template(self, mock_html_cls):
        mock_instance = MagicMock()
        mock_instance.write_pdf.return_value = b"%PDF-fake-content"
        mock_html_cls.return_value = mock_instance

        result = self.usecase.execute(self.data, [FORMAT_PDF])

        self.assertEqual(result[FORMAT_PDF], b"%PDF-fake-content")
        mock_html_cls.assert_called_once()
        kwargs = mock_html_cls.call_args.kwargs
        args = mock_html_cls.call_args.args
        # weasyprint.HTML is invoked with string=<rendered html>
        rendered = kwargs.get("string") or (args[0] if args else "")
        self.assertIn("PROTO-123", rendered)
        self.assertIn("Test Contact", rendered)

    @patch("weasyprint.HTML")
    def test_pdf_falls_back_to_media_url_without_data_uri(self, mock_html_cls):
        mock_instance = MagicMock()
        mock_instance.write_pdf.return_value = b"%PDF-fake"
        mock_html_cls.return_value = mock_instance

        # In production BuildRoomExportData always sets data_uri=None, so the
        # template falls back to the external media URL.
        data = _build_sample_data()
        for item in data["timeline"]:
            for media in item.get("medias", []):
                media["data_uri"] = None

        self.usecase.execute(data, [FORMAT_PDF])

        rendered = mock_html_cls.call_args.kwargs.get("string", "")
        self.assertIn("https://example.com/img.jpg", rendered)
        self.assertNotIn("data:image/jpeg;base64,FAKE", rendered)


class RenderRoomExportFormatSelectionTests(TestCase):
    def setUp(self):
        self.data = _build_sample_data()
        self.usecase = RenderRoomExport()

    @patch("weasyprint.HTML")
    def test_returns_both_formats_when_requested(self, mock_html_cls):
        mock_html_cls.return_value.write_pdf.return_value = b"%PDF"

        result = self.usecase.execute(self.data, [FORMAT_HTML, FORMAT_PDF])

        self.assertEqual(set(result.keys()), {FORMAT_HTML, FORMAT_PDF})

    def test_returns_only_html_when_only_html_requested(self):
        result = self.usecase.execute(self.data, [FORMAT_HTML])

        self.assertEqual(set(result.keys()), {FORMAT_HTML})

    def test_raises_for_unsupported_format(self):
        with self.assertRaises(UnsupportedExportFormatError):
            self.usecase.execute(self.data, ["docx"])

    def test_raises_for_empty_types(self):
        with self.assertRaises(UnsupportedExportFormatError):
            self.usecase.execute(self.data, [])

    def test_accepts_uppercase_types(self):
        result = self.usecase.execute(self.data, ["HTML"])

        self.assertEqual(set(result.keys()), {FORMAT_HTML})


@unittest.skipUnless(
    WEASYPRINT_AVAILABLE,
    "weasyprint not installed; skipping real PDF generation test",
)
class RenderRoomExportPdfIntegrationTests(TestCase):
    """Real WeasyPrint smoke test, skipped when the native deps are missing."""

    def test_generates_real_pdf_signature(self):
        data = _build_sample_data()
        result = RenderRoomExport().execute(data, [FORMAT_PDF])

        self.assertTrue(result[FORMAT_PDF].startswith(b"%PDF"))
