from datetime import datetime, time
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import TestCase
from rest_framework.exceptions import ValidationError

from chats.apps.projects.models import Project
from chats.apps.sectors.models import Sector
from chats.apps.sectors.utils import (
    WorkingHoursValidator,
    get_country_from_timezone,
    get_country_holidays,
    get_holidays_by_timezone,
    working_hours_validator,
)


class _SectorTestBase(TestCase):
    def setUp(self):
        cache.clear()
        self.project = Project.objects.create(name="WH Test Project")
        self.sector = Sector.objects.create(
            name="WH Sector",
            project=self.project,
            rooms_limit=2,
            work_start="09:00",
            work_end="18:00",
        )


class TestWorkingHoursValidatorEmptyConfig(_SectorTestBase):
    def test_returns_none_when_no_working_day(self):
        self.assertIsNone(
            WorkingHoursValidator().validate_working_hours(
                self.sector, datetime(2026, 5, 21, 10, 0)
            )
        )

    def test_returns_none_when_empty_working_hours(self):
        self.sector.working_day = {"working_hours": {}}
        self.sector.save()

        self.assertIsNone(
            WorkingHoursValidator().validate_working_hours(
                self.sector, datetime(2026, 5, 21, 10, 0)
            )
        )


class TestWorkingHoursValidatorClosedWeekdays(_SectorTestBase):
    def test_raises_when_weekday_in_closed_weekdays(self):
        # 2026-05-21 is Thursday (isoweekday 4)
        self.sector.working_day = {"working_hours": {"closed_weekdays": [4]}}
        self.sector.save()

        with self.assertRaises(ValidationError):
            WorkingHoursValidator().validate_working_hours(
                self.sector, datetime(2026, 5, 21, 10, 0)
            )


class TestWorkingHoursValidatorWeekdaySchedule(_SectorTestBase):
    def test_passes_when_inside_dict_interval(self):
        self.sector.working_day = {
            "working_hours": {
                "schedules": {"thursday": {"start": "09:00", "end": "18:00"}}
            }
        }
        self.sector.save()

        WorkingHoursValidator().validate_working_hours(
            self.sector, datetime(2026, 5, 21, 10, 0)
        )

    def test_raises_when_outside_dict_interval(self):
        self.sector.working_day = {
            "working_hours": {
                "schedules": {"thursday": {"start": "09:00", "end": "18:00"}}
            }
        }
        self.sector.save()

        with self.assertRaises(ValidationError):
            WorkingHoursValidator().validate_working_hours(
                self.sector, datetime(2026, 5, 21, 20, 0)
            )

    def test_raises_when_dict_interval_missing_keys(self):
        self.sector.working_day = {
            "working_hours": {"schedules": {"thursday": {"start": "09:00"}}}
        }
        self.sector.save()

        with self.assertRaises(ValidationError):
            WorkingHoursValidator().validate_working_hours(
                self.sector, datetime(2026, 5, 21, 10, 0)
            )

    def test_passes_when_inside_one_of_list_intervals(self):
        self.sector.working_day = {
            "working_hours": {
                "schedules": {
                    "thursday": [
                        {"start": "08:00", "end": "10:00"},
                        {"start": "13:00", "end": "17:00"},
                    ]
                }
            }
        }
        self.sector.save()

        WorkingHoursValidator().validate_working_hours(
            self.sector, datetime(2026, 5, 21, 14, 0)
        )

    def test_raises_when_outside_all_list_intervals(self):
        self.sector.working_day = {
            "working_hours": {
                "schedules": {
                    "thursday": [
                        {"start": "08:00", "end": "10:00"},
                        {"start": "13:00", "end": "17:00"},
                    ]
                }
            }
        }
        self.sector.save()

        with self.assertRaises(ValidationError):
            WorkingHoursValidator().validate_working_hours(
                self.sector, datetime(2026, 5, 21, 12, 0)
            )

    def test_skips_invalid_list_interval(self):
        self.sector.working_day = {
            "working_hours": {
                "schedules": {
                    "thursday": [
                        {"start": "08:00"},
                        {"start": "13:00", "end": "17:00"},
                    ]
                }
            }
        }
        self.sector.save()

        WorkingHoursValidator().validate_working_hours(
            self.sector, datetime(2026, 5, 21, 14, 0)
        )

    def test_raises_when_unknown_day_cfg_type(self):
        self.sector.working_day = {
            "working_hours": {"schedules": {"thursday": "weird"}}
        }
        self.sector.save()

        with self.assertRaises(ValidationError):
            WorkingHoursValidator().validate_working_hours(
                self.sector, datetime(2026, 5, 21, 10, 0)
            )

    def test_raises_when_weekday_not_configured(self):
        # No schedules at all for the day
        self.sector.working_day = {"working_hours": {"schedules": {}}}
        self.sector.save()

        with self.assertRaises(ValidationError):
            WorkingHoursValidator().validate_working_hours(
                self.sector, datetime(2026, 5, 21, 10, 0)
            )


class TestWorkingHoursValidatorStaticHolidays(_SectorTestBase):
    def test_static_holiday_closed_raises(self):
        self.sector.working_day = {
            "working_hours": {
                "schedules": {"thursday": {"start": "09:00", "end": "18:00"}},
                "static_holidays": {"2026-05-21": {"closed": True}},
            }
        }
        self.sector.save()

        with self.assertRaises(ValidationError) as ctx:
            WorkingHoursValidator().validate_working_hours(
                self.sector, datetime(2026, 5, 21, 10, 0)
            )
        self.assertIn("holiday", str(ctx.exception).lower())

    def test_static_holiday_open_with_hours_passes_inside_window(self):
        self.sector.working_day = {
            "working_hours": {
                "schedules": {"thursday": {"start": "09:00", "end": "18:00"}},
                "static_holidays": {
                    "2026-05-21": {
                        "closed": False,
                        "start": "10:00",
                        "end": "14:00",
                    }
                },
            }
        }
        self.sector.save()

        # Inside holiday window: no error from static_holiday but still
        # needs to be inside the weekday schedule (also passing)
        WorkingHoursValidator().validate_working_hours(
            self.sector, datetime(2026, 5, 21, 12, 0)
        )

    def test_static_holiday_open_with_hours_raises_outside_window(self):
        self.sector.working_day = {
            "working_hours": {
                "schedules": {"thursday": {"start": "09:00", "end": "20:00"}},
                "static_holidays": {
                    "2026-05-21": {
                        "closed": False,
                        "start": "10:00",
                        "end": "14:00",
                    }
                },
            }
        }
        self.sector.save()

        with self.assertRaises(ValidationError):
            WorkingHoursValidator().validate_working_hours(
                self.sector, datetime(2026, 5, 21, 19, 0)
            )


class TestWorkingHoursValidatorDynamicHolidays(_SectorTestBase):
    @patch("chats.apps.sectors.models.SectorHoliday")
    def test_closed_dynamic_holiday_raises(self, mock_sector_holiday):
        self.sector.working_day = {
            "working_hours": {
                "schedules": {"thursday": {"start": "09:00", "end": "18:00"}}
            }
        }
        self.sector.save()

        fake_holiday = MagicMock()
        fake_holiday.day_type = "closed"
        fake_holiday.start_time = None
        fake_holiday.end_time = None
        fake_holiday.description = "Local holiday"
        mock_sector_holiday.objects.filter.return_value.filter.return_value.first.return_value = (
            fake_holiday
        )

        with self.assertRaises(ValidationError) as ctx:
            WorkingHoursValidator().validate_working_hours(
                self.sector, datetime(2026, 5, 21, 10, 0)
            )
        self.assertIn("holiday", str(ctx.exception).lower())

    @patch("chats.apps.sectors.models.SectorHoliday")
    def test_custom_hours_holiday_passes_in_window(self, mock_sector_holiday):
        self.sector.working_day = {
            "working_hours": {
                "schedules": {"thursday": {"start": "09:00", "end": "18:00"}}
            }
        }
        self.sector.save()

        fake_holiday = MagicMock()
        fake_holiday.day_type = "custom_hours"
        fake_holiday.start_time = time(10, 0)
        fake_holiday.end_time = time(14, 0)
        fake_holiday.description = "Half day"
        mock_sector_holiday.objects.filter.return_value.filter.return_value.first.return_value = (
            fake_holiday
        )

        WorkingHoursValidator().validate_working_hours(
            self.sector, datetime(2026, 5, 21, 12, 0)
        )

    @patch("chats.apps.sectors.models.SectorHoliday")
    def test_custom_hours_holiday_raises_outside_window(self, mock_sector_holiday):
        self.sector.working_day = {
            "working_hours": {
                "schedules": {"thursday": {"start": "09:00", "end": "18:00"}}
            }
        }
        self.sector.save()

        fake_holiday = MagicMock()
        fake_holiday.day_type = "custom_hours"
        fake_holiday.start_time = time(10, 0)
        fake_holiday.end_time = time(14, 0)
        fake_holiday.description = "Half day"
        mock_sector_holiday.objects.filter.return_value.filter.return_value.first.return_value = (
            fake_holiday
        )

        with self.assertRaises(ValidationError):
            WorkingHoursValidator().validate_working_hours(
                self.sector, datetime(2026, 5, 21, 15, 0)
            )


class TestWorkingHoursValidatorWeekend(_SectorTestBase):
    def test_weekend_passes_when_inside_saturday_schedule(self):
        # 2026-05-23 Saturday (isoweekday 6)
        self.sector.working_day = {
            "working_hours": {
                "schedules": {
                    "saturday": {"start": "10:00", "end": "14:00"}
                }
            }
        }
        self.sector.save()

        WorkingHoursValidator().validate_working_hours(
            self.sector, datetime(2026, 5, 23, 11, 0)
        )

    def test_weekend_raises_when_no_saturday_schedule(self):
        self.sector.working_day = {"working_hours": {"schedules": {}}}
        self.sector.save()

        with self.assertRaises(ValidationError):
            WorkingHoursValidator().validate_working_hours(
                self.sector, datetime(2026, 5, 23, 11, 0)
            )

    def test_weekend_sunday_schedule(self):
        # 2026-05-24 Sunday (isoweekday 7)
        self.sector.working_day = {
            "working_hours": {
                "schedules": {"sunday": {"start": "10:00", "end": "14:00"}}
            }
        }
        self.sector.save()

        WorkingHoursValidator().validate_working_hours(
            self.sector, datetime(2026, 5, 24, 11, 0)
        )


class TestParseTimeCached(TestCase):
    def setUp(self):
        cache.clear()

    def test_parses_and_caches_time(self):
        first = WorkingHoursValidator._parse_time_cached("12:30")
        cached = WorkingHoursValidator._parse_time_cached("12:30")
        self.assertEqual(first, cached)
        self.assertEqual(first, time(12, 30))


class TestCountryHolidays(TestCase):
    def test_returns_empty_for_unknown_country_code(self):
        self.assertEqual(get_country_holidays("ZZ", year=2026), {})

    def test_returns_empty_for_empty_country_code(self):
        self.assertEqual(get_country_holidays("", year=2026), {})
        self.assertEqual(get_country_holidays(None, year=2026), {})

    def test_returns_known_country_holidays(self):
        holidays = get_country_holidays("BR", year=2026)
        self.assertIsInstance(holidays, dict)
        # Expect at least one holiday for Brazil
        self.assertTrue(len(holidays) > 0)

    def test_falls_back_to_current_year_when_year_none(self):
        # Should not raise; defaults to current year
        result = get_country_holidays("BR")
        self.assertIsInstance(result, dict)


class TestCountryFromTimezone(TestCase):
    def test_returns_none_for_empty_timezone(self):
        self.assertIsNone(get_country_from_timezone(""))
        self.assertIsNone(get_country_from_timezone(None))

    def test_returns_country_for_known_timezone(self):
        self.assertEqual(get_country_from_timezone("America/Sao_Paulo"), "BR")

    def test_returns_country_case_insensitive(self):
        self.assertEqual(get_country_from_timezone("america/sao_paulo"), "BR")

    def test_returns_country_by_city_fallback(self):
        # Use a city-only string to drive the city fallback
        self.assertIsNotNone(get_country_from_timezone("Sao_Paulo"))

    def test_returns_none_for_unknown_timezone(self):
        self.assertIsNone(get_country_from_timezone("Unknown/Place"))


class TestHolidaysByTimezone(TestCase):
    def test_returns_holidays_for_known_timezone(self):
        holidays = get_holidays_by_timezone("America/Sao_Paulo", year=2026)
        self.assertIsInstance(holidays, dict)


class TestSingletonInstance(TestCase):
    def test_module_level_singleton_exists(self):
        self.assertIsInstance(working_hours_validator, WorkingHoursValidator)
