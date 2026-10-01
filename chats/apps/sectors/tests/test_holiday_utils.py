from datetime import date, datetime, timezone as dt_timezone
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from chats.apps.sectors.utils import (
    get_country_from_timezone,
    get_country_holidays,
    get_holidays_by_timezone,
)


class GetCountryFromTimezoneTests(SimpleTestCase):
    def test_returns_br_for_sao_paulo(self):
        self.assertEqual(get_country_from_timezone("America/Sao_Paulo"), "BR")

    def test_returns_none_for_empty_timezone(self):
        self.assertIsNone(get_country_from_timezone(""))
        self.assertIsNone(get_country_from_timezone(None))

    def test_normalizes_spaces_in_timezone(self):
        self.assertEqual(get_country_from_timezone("America/Sao Paulo"), "BR")

    def test_matches_city_name_case_insensitively(self):
        self.assertEqual(get_country_from_timezone("sao_paulo"), "BR")

    def test_returns_none_for_unknown_timezone(self):
        self.assertIsNone(get_country_from_timezone("Not/A_Real_Zone"))


class GetCountryHolidaysTests(SimpleTestCase):
    def test_returns_empty_dict_when_country_code_is_missing(self):
        self.assertEqual(get_country_holidays(""), {})
        self.assertEqual(get_country_holidays(None), {})

    def test_returns_empty_dict_for_unknown_country(self):
        self.assertEqual(get_country_holidays("ZZ"), {})

    def test_returns_holidays_for_brazil(self):
        holidays = get_country_holidays("BR", year=2026)

        self.assertIsInstance(holidays, dict)
        self.assertGreater(len(holidays), 0)
        self.assertTrue(all(isinstance(day, date) for day in holidays.keys()))

    @patch("chats.apps.sectors.utils.timezone.now")
    def test_uses_current_year_when_year_is_none(self, mock_now):
        mock_now.return_value = datetime(2025, 6, 1, tzinfo=dt_timezone.utc)

        with patch("chats.apps.sectors.utils.registry.get") as mock_registry:
            calendar = MagicMock()
            calendar.holidays.return_value = [(date(2025, 1, 1), "New Year")]
            mock_registry.return_value = lambda: calendar

            holidays = get_country_holidays("BR")

        calendar.holidays.assert_called_once_with(2025)
        self.assertEqual(holidays, {date(2025, 1, 1): "New Year"})

    @patch("chats.apps.sectors.utils.registry.get", side_effect=RuntimeError("boom"))
    def test_returns_empty_dict_when_registry_raises(self, _mock_registry):
        self.assertEqual(get_country_holidays("BR", year=2026), {})


class GetHolidaysByTimezoneTests(SimpleTestCase):
    @patch("chats.apps.sectors.utils.get_country_holidays")
    @patch("chats.apps.sectors.utils.get_country_from_timezone", return_value="BR")
    def test_delegates_to_country_helpers(self, mock_country, mock_holidays):
        mock_holidays.return_value = {date(2026, 1, 1): "New Year"}

        result = get_holidays_by_timezone("America/Sao_Paulo", year=2026)

        mock_country.assert_called_once_with("America/Sao_Paulo")
        mock_holidays.assert_called_once_with("BR", 2026)
        self.assertEqual(result, {date(2026, 1, 1): "New Year"})
