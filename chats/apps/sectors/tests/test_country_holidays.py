from datetime import date
from unittest.mock import MagicMock, patch

import requests
from django.core.cache import cache
from django.test import SimpleTestCase

from chats.apps.sectors.utils import (
    BRASIL_API_HOLIDAYS_TIMEOUT,
    BRASIL_API_HOLIDAYS_URL,
    BRASIL_HOLIDAYS_CACHE_KEY,
    get_country_holidays,
)


class BrazilOfficialHolidaysTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def _api_payload(self):
        return [
            {
                "date": "2026-01-01",
                "name": "Confraternização mundial",
                "type": "national",
            },
            {"date": "2026-12-25", "name": "Natal", "type": "national"},
        ]

    def _mock_response(self, payload):
        response = MagicMock()
        response.json.return_value = payload
        response.raise_for_status.return_value = None
        return response

    @patch("chats.apps.sectors.utils.requests.get")
    def test_brazil_holidays_come_from_brasil_api(self, mock_get):
        mock_get.return_value = self._mock_response(self._api_payload())

        holidays = get_country_holidays("BR", 2026)

        self.assertEqual(
            holidays,
            {
                date(2026, 1, 1): "Confraternização mundial",
                date(2026, 12, 25): "Natal",
            },
        )
        mock_get.assert_called_once_with(
            BRASIL_API_HOLIDAYS_URL.format(year=2026),
            timeout=BRASIL_API_HOLIDAYS_TIMEOUT,
        )

    @patch("chats.apps.sectors.utils.requests.get")
    def test_brazil_holidays_use_cache(self, mock_get):
        mock_get.return_value = self._mock_response(self._api_payload())

        first = get_country_holidays("br", 2026)
        second = get_country_holidays("BR", 2026)

        self.assertEqual(first, second)
        mock_get.assert_called_once()

    @patch("chats.apps.sectors.utils.requests.get")
    def test_brazil_holidays_fall_back_to_cached_copy(self, mock_get):
        mock_get.return_value = self._mock_response(self._api_payload())
        get_country_holidays("BR", 2026)

        cache.delete(BRASIL_HOLIDAYS_CACHE_KEY.format(year=2026))
        mock_get.side_effect = requests.RequestException("brasil api down")

        holidays = get_country_holidays("BR", 2026)

        self.assertEqual(holidays[date(2026, 12, 25)], "Natal")

    @patch("chats.apps.sectors.utils.requests.get")
    def test_brazil_holidays_return_empty_when_api_and_cache_fail(self, mock_get):
        mock_get.side_effect = requests.RequestException("brasil api down")

        self.assertEqual(get_country_holidays("BR", 2026), {})

    @patch("chats.apps.sectors.utils.requests.get")
    @patch("chats.apps.sectors.utils.registry.get")
    def test_other_countries_keep_workalendar(self, mock_registry, mock_get):
        calendar = MagicMock()
        calendar.holidays.return_value = [(date(2026, 7, 4), "Independence Day")]
        mock_registry.return_value.return_value = calendar

        holidays = get_country_holidays("US", 2026)

        self.assertEqual(holidays, {date(2026, 7, 4): "Independence Day"})
        mock_get.assert_not_called()
