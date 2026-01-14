from unittest.mock import patch

from django.test import TestCase

from chats.apps.archive_chats.helpers import (
    get_filename_from_url,
    generate_unique_filename,
)


class TestGetFilenameFromUrl(TestCase):
    def test_get_filename_from_url(self):
        url = "https://example.com/path/to/file.txt"
        self.assertEqual(get_filename_from_url(url), "file.txt")


class TestGenerateUniqueFilename(TestCase):

    def test_generate_unique_filename_when_original_filename_is_not_in_used_filenames(
        self,
    ):
        original_filename = "file.txt"
        used_filenames = {}

        new_filename = generate_unique_filename(original_filename, used_filenames)

        self.assertEqual(new_filename, "file.txt")
        self.assertNotIn(new_filename, used_filenames)

    @patch("chats.apps.archive_chats.helpers.get_random_string")
    def test_generate_unique_filename(self, mock_get_random_string):
        mock_get_random_string.return_value = "12345678"
        original_filename = "file.txt"
        used_filenames = {"file.txt"}

        new_filename = generate_unique_filename(original_filename, used_filenames)

        self.assertNotIn(new_filename, used_filenames)
        self.assertEqual(new_filename, "file_12345678.txt")
        mock_get_random_string.assert_called_once_with(8)

    @patch("chats.apps.archive_chats.helpers.get_random_string")
    def test_generate_unique_filenames_exhausting_attempts(
        self, mock_get_random_string
    ):
        mock_get_random_string.side_effect = [
            "11111111",
            "22222222",
            "33333333",
            "44444444",
            "55555555",
            "66666666",
        ]

        original_filename = "file.txt"
        used_filenames = {
            "file.txt",
            "file_11111111.txt",
            "file_22222222.txt",
            "file_33333333.txt",
            "file_44444444.txt",
            "file_55555555.txt",
        }

        with self.assertRaises(ValueError) as context:
            generate_unique_filename(original_filename, used_filenames)

        self.assertEqual(
            str(context.exception),
            "Failed to generate a unique filename after 5 attempts",
        )
        mock_get_random_string.assert_called_with(8)
