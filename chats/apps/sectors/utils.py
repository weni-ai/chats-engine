import json
import logging

import pendulum
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError
from workalendar.registry import registry

from chats.core.cache import CacheClient

logger = logging.getLogger(__name__)


class WorkingHoursValidator:
    """
    Utility for validating sector working hours.
    Checks configurable holidays, static holidays, weekends and closed days.
    """

    def __init__(self):
        self.cache_client = CacheClient()

    def validate_working_hours(self, sector, created_on):
        """
        Main method for working hours validation.

        Args:
            sector: Sector model instance
            created_on: datetime of room creation

        Raises:
            ValidationError: If the room cannot be created at this time
        """
        working_hours_config = (
            sector.working_day.get("working_hours", {}) if sector.working_day else {}
        )

        if not working_hours_config:
            return

        weekday = created_on.isoweekday()
        current_date = created_on.date()
        current_time = created_on.time()

        closed_weekdays = working_hours_config.get("closed_weekdays", [])
        if weekday in closed_weekdays:
            raise ValidationError(
                {"detail": _("Contact cannot be done outside working hours")}
            )

        if 1 <= weekday <= 5:
            holiday = self._get_cached_holiday(sector.uuid, current_date)
            if holiday:
                self._validate_holiday(holiday, current_time, created_on)
                return
            else:
                self._check_static_holidays_fast(
                    working_hours_config, current_date, current_time, created_on
                )
            schedules = working_hours_config.get("schedules", {})
            weekday_map = {
                1: "monday",
                2: "tuesday",
                3: "wednesday",
                4: "thursday",
                5: "friday",
            }
            day_key = weekday_map.get(weekday)
            day_cfg = schedules.get(day_key)
            if day_cfg is None:
                raise ValidationError(
                    {"detail": _("Contact cannot be done outside working hours")}
                )
            self._validate_day_schedules_generic(day_cfg, current_time)
            return

        self._full_validation(
            sector,
            working_hours_config,
            weekday,
            current_date,
            current_time,
            created_on,
        )

    def _get_cached_holiday(self, sector_uuid, date):
        """
        Search for holiday with 5 minute cache (simple and effective)
        """
        cache_key = f"holiday:{sector_uuid}:{date}"
        cached_result = self.cache_client.get(cache_key)

        if cached_result is not None:
            if cached_result == "null":
                return None
            return json.loads(cached_result)

        from chats.apps.sectors.models import SectorHoliday

        holiday = (
            SectorHoliday.objects.filter(sector__uuid=sector_uuid, is_deleted=False)
            .filter(Q(date=date) | Q(date__lte=date, date_end__gte=date))
            .first()
        )

        if holiday:
            holiday_data = {
                "day_type": holiday.day_type,
                "start_time": holiday.start_time.strftime("%H:%M")
                if holiday.start_time
                else None,
                "end_time": holiday.end_time.strftime("%H:%M")
                if holiday.end_time
                else None,
                "description": holiday.description,
            }
            self.cache_client.set(cache_key, json.dumps(holiday_data), ex=300)
            return holiday_data
        else:
            self.cache_client.set(cache_key, "null", ex=300)
            return None

    def _check_static_holidays_fast(
        self, working_hours_config, current_date, current_time, created_on
    ):
        """
        Fast verification of static holidays (no additional cache since it's already in memory)
        """
        static_holidays = working_hours_config.get("static_holidays", {})
        if not static_holidays:
            return

        date_str = current_date.strftime("%Y-%m-%d")
        month_day_str = current_date.strftime("%m-%d")

        holiday_config = static_holidays.get(date_str) or static_holidays.get(
            month_day_str
        )

        if holiday_config:
            self._validate_static_holiday_fast(holiday_config, current_time, created_on)

    def _validate_static_holiday_fast(self, holiday_config, current_time, created_on):
        """
        Optimized validation of static holiday
        """
        if holiday_config.get("closed", True):
            raise ValidationError(
                {"detail": _("Contact cannot be done outside working hours")}
            )

        start_str = holiday_config.get("start")
        end_str = holiday_config.get("end")

        if start_str and end_str:
            start_time = self._parse_time_cached(start_str)
            end_time = self._parse_time_cached(end_str)

            if not (start_time <= current_time <= end_time):
                raise ValidationError(
                    {"detail": _("Contact cannot be done outside working hours")}
                )

    def _validate_holiday(self, holiday_data, current_time, created_on):
        """
        Optimized validation of holiday
        """
        if holiday_data["day_type"] == "closed":
            raise ValidationError(
                {"detail": _("Contact cannot be done outside working hours")}
            )

        start_str = holiday_data.get("start_time")
        end_str = holiday_data.get("end_time")

        if start_str and end_str:
            start_time = self._parse_time_cached(start_str)
            end_time = self._parse_time_cached(end_str)

            if not (start_time <= current_time <= end_time):
                raise ValidationError(
                    {"detail": _("Contact cannot be done outside working hours")}
                )

    def _validate_day_schedules_generic(self, day_cfg, current_time):
        """
        Validate a day from:
          - dict {"start": "HH:MM", "end": "HH:MM"} (um intervalo)
          - list[{"start": "HH:MM", "end": "HH:MM"}, ...] (múltiplos intervalos)
        Passes if at least one interval contains the time.
        """
        if isinstance(day_cfg, dict):
            start_str = day_cfg.get("start")
            end_str = day_cfg.get("end")
            if not start_str or not end_str:
                raise ValidationError(
                    {"detail": _("Contact cannot be done outside working hours")}
                )
            start_time = self._parse_time_cached(start_str)
            end_time = self._parse_time_cached(end_str)

            if start_time <= current_time <= end_time:
                return
            raise ValidationError(
                {"detail": _("Contact cannot be done outside working hours")}
            )

        if isinstance(day_cfg, list):
            any_ok = False
            for interval in day_cfg:
                try:
                    start_str = interval.get("start")
                    end_str = interval.get("end")
                    if not start_str or not end_str:
                        continue
                    start_time = self._parse_time_cached(start_str)
                    end_time = self._parse_time_cached(end_str)
                    if start_time <= current_time <= end_time:
                        any_ok = True
                        break
                except Exception:
                    continue
            if not any_ok:
                raise ValidationError(
                    {"detail": _("Contact cannot be done outside working hours")}
                )
            return

        raise ValidationError(
            {"detail": _("Contact cannot be done outside working hours")}
        )

    @staticmethod
    def _parse_time_cached(time_str):
        """
        Cache of common time parsing
        """
        cache_key = f"parsed_time:{time_str}"
        cached_time = cache.get(cache_key)

        if cached_time is not None:
            return cached_time

        parsed_time = pendulum.parse(time_str).time()
        cache.set(cache_key, parsed_time, 86400)
        return parsed_time

    def _full_validation(
        self,
        sector,
        working_hours_config,
        weekday,
        current_date,
        current_time,
        created_on,
    ):
        """
        Full validation for complex cases (weekends, closed days)
        """
        holiday = self._get_cached_holiday(sector.uuid, current_date)
        if holiday:
            self._validate_holiday(holiday, current_time, created_on)
            return

        self._check_static_holidays_fast(
            working_hours_config, current_date, current_time, created_on
        )

        if weekday in (6, 7):
            schedules = working_hours_config.get("schedules", {})
            day_key = "saturday" if weekday == 6 else "sunday"
            day_cfg = schedules.get(day_key)
            if day_cfg is None:
                raise ValidationError(
                    {"detail": _("Contact cannot be done outside working hours")}
                )
            self._validate_day_schedules_generic(day_cfg, current_time)

    def _validate_day_schedule_fast(self, day_config, current_time, created_on):
        """
        Backward-compat: single interval validation (deprecated internally).
        """
        start_str = day_config.get("start")
        end_str = day_config.get("end")

        if not start_str or not end_str:
            raise ValidationError(
                {"detail": _("Contact cannot be done outside working hours")}
            )

        start_time = self._parse_time_cached(start_str)
        end_time = self._parse_time_cached(end_str)

        if not (start_time <= current_time <= end_time):
            raise ValidationError(
                {"detail": _("Contact cannot be done outside working hours")}
            )


working_hours_validator = WorkingHoursValidator()


def get_country_holidays(country_code, year=None, language="en"):
    """
    Search official holidays of the country using the workalendar library

    Args:
        country_code: Código do país (BR, US, etc.)
        year: Year (default: current year)
        language: Language of the holiday names (not used in workalendar)

    Returns:
        dict: {date: holiday_name}
    """
    if year is None:
        year = timezone.now().year

    try:
        if not country_code:
            logger.warning("No country code provided; returning empty holidays.")
            return {}

        calendar_class = registry.get(country_code.upper())

        if calendar_class:
            calendar = calendar_class()
            holidays_list = calendar.holidays(year)
            return {
                holiday_date: holiday_name
                for holiday_date, holiday_name in holidays_list
            }
        else:
            logger.warning(f"Calendar not found for country code: {country_code}")
            return {}

    except Exception as e:
        logger.warning(f"Error getting holidays for country {country_code}: {str(e)}")
        return {}


def get_country_from_timezone(timezone_str):
    """
    Maps timezone to country code

    Args:
        timezone_str: String of timezone (ex: "America/Sao_Paulo")

    Returns:
        str: Country code (ex: "BR")
    """
    import pytz

    if not timezone_str:
        logger.warning("Empty timezone string; cannot infer country.")
        return None

    tz_input = str(timezone_str).strip().replace(" ", "_")

    timezone_to_country_map = {}
    for country_code, timezones in pytz.country_timezones.items():
        for tz in timezones:
            timezone_to_country_map[tz] = country_code

    country = timezone_to_country_map.get(tz_input)
    if country:
        return country

    lower_map = {k.lower(): v for k, v in timezone_to_country_map.items()}
    country = lower_map.get(tz_input.lower())
    if country:
        return country

    city = tz_input.split("/")[-1].lower()
    for tz, cc in timezone_to_country_map.items():
        if tz.split("/")[-1].lower() == city:
            return cc

    logger.warning(f"Timezone '{timezone_str}' not found in pytz mapping.")
    return None


def get_holidays_by_timezone(timezone_str, year=None):
    """
    Get holidays based on timezone (automatically detects country)

    Args:
        timezone_str: Timezone string (ex: "America/Sao_Paulo")
        year: Year (default: current year)

    Returns:
        dict: {date: holiday_name}
    """
    country_code = get_country_from_timezone(timezone_str)
    return get_country_holidays(country_code, year)
