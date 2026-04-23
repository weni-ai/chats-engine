from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from django.test import TestCase

from chats.apps.archive_chats.expiration import calculate_archive_task_expiration_dt


class TestExpiration(TestCase):
    def test_calculate_archive_task_expiration_dt_when_max_hour_is_in_the_same_day(
        self,
    ):
        now = datetime(2024, 1, 1, 3, 0, 0, tzinfo=timezone.utc)

        with patch("chats.apps.archive_chats.expiration.datetime") as mock_datetime:
            mock_datetime.now.return_value = now
            mock_datetime.strptime.side_effect = datetime.strptime
            mock_datetime.combine.side_effect = datetime.combine

            expiration_dt = calculate_archive_task_expiration_dt("08:59")

        self.assertEqual(expiration_dt.hour, 8)
        self.assertEqual(expiration_dt.minute, 59)
        self.assertEqual(expiration_dt.second, 0)
        self.assertEqual(expiration_dt.microsecond, 0)
        self.assertEqual(expiration_dt.date(), now.date())
        self.assertEqual(expiration_dt.tzinfo, timezone.utc)

    def test_calculate_archive_task_expiration_dt_when_max_hour_is_in_the_next_day(
        self,
    ):
        now = datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc)

        with patch("chats.apps.archive_chats.expiration.datetime") as mock_datetime:
            mock_datetime.now.return_value = now
            mock_datetime.strptime.side_effect = datetime.strptime
            mock_datetime.combine.side_effect = datetime.combine

            expiration_dt = calculate_archive_task_expiration_dt("08:59")

        self.assertEqual(expiration_dt.hour, 8)
        self.assertEqual(expiration_dt.minute, 59)
        self.assertEqual(expiration_dt.second, 0)
        self.assertEqual(expiration_dt.microsecond, 0)
        self.assertEqual(expiration_dt.date(), now.date() + timedelta(days=1))
        self.assertEqual(expiration_dt.tzinfo, timezone.utc)
