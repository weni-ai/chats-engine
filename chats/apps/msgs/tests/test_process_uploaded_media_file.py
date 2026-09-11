from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from chats.apps.api.v1.msgs.serializers import process_uploaded_media_file


class ProcessUploadedMediaFileTests(SimpleTestCase):
    def _media(self, name="file.jpg"):
        media = SimpleNamespace(name=name, file=BytesIO(b"raw-bytes"))
        return media

    @override_settings(FILE_CHECK_CONTENT_TYPE="application/octet-stream")
    @patch(
        "chats.apps.api.v1.msgs.serializers.magic.from_buffer", return_value="image/png"
    )
    def test_sets_content_type_for_regular_file(self, mock_magic):
        media = self._media()
        result = process_uploaded_media_file({"media_file": media})

        self.assertEqual(result["content_type"], "image/png")
        mock_magic.assert_called_once()

    @override_settings(
        FILE_CHECK_CONTENT_TYPE="application/octet-stream",
        UNPERMITTED_AUDIO_TYPES=["ogg"],
        AUDIO_TYPE_TO_CONVERT="mp3",
        AUDIO_CODEC_TO_CONVERT="",
        AUDIO_EXTENSION_TO_CONVERT="mp3",
    )
    @patch("chats.apps.api.v1.msgs.serializers.AudioSegment.from_file")
    @patch("chats.apps.api.v1.msgs.serializers.magic.from_buffer")
    def test_converts_unpermitted_audio(self, mock_magic, mock_from_file):
        mock_magic.side_effect = ["ogg", "audio/mpeg"]
        exported = MagicMock()
        mock_from_file.return_value.export = exported
        media = self._media(name="voice.ogg")

        result = process_uploaded_media_file({"media_file": media})

        exported.assert_called_once()
        self.assertEqual(media.name, "voice.mp3")
        self.assertEqual(result["content_type"], "audio/mpeg")
