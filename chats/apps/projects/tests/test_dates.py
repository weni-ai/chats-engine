from django.test import TestCase

from chats.apps.projects.dates import parse_date_with_timezone
import pytz
from datetime import datetime


class TestParseDateWithTimezone(TestCase):
    def test_parse_date_with_timezone_date_only(self):
        """Test parsing date-only format (YYYY-MM-DD)"""
        project_timezone = "America/Sao_Paulo"

        result = parse_date_with_timezone(
            "2024-01-01", project_timezone, is_end_date=False
        )
        expected_tz = pytz.timezone(project_timezone)
        expected = expected_tz.localize(
            datetime.strptime("2024-01-01 00:00:00", "%Y-%m-%d %H:%M:%S")
        )
        self.assertEqual(result, expected)

        result = parse_date_with_timezone(
            "2024-01-01", project_timezone, is_end_date=True
        )
        expected = expected_tz.localize(
            datetime.strptime("2024-01-01 23:59:59", "%Y-%m-%d %H:%M:%S")
        )
        self.assertEqual(result, expected)

    def test_parse_date_with_timezone_datetime_no_timezone(self):
        """Test parsing datetime format without timezone"""
        project_timezone = "America/Sao_Paulo"

        # Test ISO datetime format
        result = parse_date_with_timezone(
            "2024-01-01T14:30:00", project_timezone, is_end_date=False
        )
        expected_tz = pytz.timezone(project_timezone)
        expected = expected_tz.localize(
            datetime.strptime("2024-01-01 14:30:00", "%Y-%m-%d %H:%M:%S")
        )
        self.assertEqual(result, expected)

        # Test space-separated datetime format
        result = parse_date_with_timezone(
            "2024-01-01 14:30:00", project_timezone, is_end_date=False
        )
        expected = expected_tz.localize(
            datetime.strptime("2024-01-01 14:30:00", "%Y-%m-%d %H:%M:%S")
        )
        self.assertEqual(result, expected)

    def test_parse_date_with_timezone_datetime_with_timezone(self):
        """Test parsing datetime format with existing timezone (should convert to project timezone)"""
        project_timezone = "America/Sao_Paulo"

        # Create a datetime with UTC timezone
        utc_tz = pytz.timezone("UTC")
        utc_datetime = utc_tz.localize(
            datetime.strptime("2024-01-01 14:30:00", "%Y-%m-%d %H:%M:%S")
        )

        # Convert to string format that includes timezone info (ISO format)
        utc_datetime_str = utc_datetime.isoformat()

        # Test that it converts to project timezone
        result = parse_date_with_timezone(
            utc_datetime_str, project_timezone, is_end_date=False
        )
        expected_tz = pytz.timezone(project_timezone)
        expected = utc_datetime.astimezone(expected_tz)
        self.assertEqual(result, expected)

    def test_parse_date_with_timezone_offset_format(self):
        """Test parsing datetime format with timezone offset (e.g., -03:00)"""
        project_timezone = "America/Sao_Paulo"

        # Test negative timezone offset
        result = parse_date_with_timezone(
            "2025-01-01T00:00:00-03:00", project_timezone, is_end_date=False
        )
        expected_tz = pytz.timezone(project_timezone)
        # The input is 2025-01-01 00:00:00 in -03:00 timezone
        # This should convert to the project timezone
        input_dt = datetime.fromisoformat("2025-01-01T00:00:00-03:00")
        expected = input_dt.astimezone(expected_tz)
        self.assertEqual(result, expected)

        # Test positive timezone offset
        result = parse_date_with_timezone(
            "2025-01-01T12:30:00+05:30", project_timezone, is_end_date=False
        )
        input_dt = datetime.fromisoformat("2025-01-01T12:30:00+05:30")
        expected = input_dt.astimezone(expected_tz)
        self.assertEqual(result, expected)

        # Test UTC timezone (Z format)
        result = parse_date_with_timezone(
            "2025-01-01T15:45:00Z", project_timezone, is_end_date=False
        )
        input_dt = datetime.fromisoformat("2025-01-01T15:45:00+00:00")
        expected = input_dt.astimezone(expected_tz)
        self.assertEqual(result, expected)

    def test_parse_date_with_timezone_edge_cases(self):
        """Test edge cases for date parsing"""
        project_timezone = "America/Sao_Paulo"

        # Test None input
        result = parse_date_with_timezone(None, project_timezone, is_end_date=False)
        self.assertIsNone(result)

        # Test empty string
        result = parse_date_with_timezone("", project_timezone, is_end_date=False)
        self.assertIsNone(result)
