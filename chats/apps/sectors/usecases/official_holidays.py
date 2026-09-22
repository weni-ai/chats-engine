from datetime import datetime

from django.utils import timezone
from rest_framework import status

from chats.apps.projects.models import Project
from chats.apps.projects.models.models import ProjectPermission
from chats.apps.sectors.models import Sector, SectorHoliday
from chats.apps.sectors.utils import get_country_from_timezone, get_country_holidays


class OfficialHolidayRequestError(Exception):
    def __init__(self, detail, status_code):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class ListOfficialHolidaysUseCase:
    def execute(self, user, project_uuid, year_param):
        if not project_uuid:
            raise OfficialHolidayRequestError(
                "Parameter 'project' is required",
                status.HTTP_400_BAD_REQUEST,
            )

        try:
            project = Project.objects.get(uuid=project_uuid)
        except Project.DoesNotExist:
            raise OfficialHolidayRequestError(
                "Project not found",
                status.HTTP_404_NOT_FOUND,
            )

        has_access = ProjectPermission.objects.filter(
            user=user, project=project
        ).exists()
        if not has_access:
            raise OfficialHolidayRequestError(
                "You dont have permission in this project.",
                status.HTTP_403_FORBIDDEN,
            )

        year = self._parse_year(year_param, project)
        country_code = get_country_from_timezone(str(project.timezone))
        official_holidays = get_country_holidays(country_code, year)

        holidays_list = [
            {"date": hd.strftime("%Y-%m-%d"), "name": hn, "country_code": country_code}
            for hd, hn in official_holidays.items()
        ]

        return {
            "country_code": country_code,
            "year": year,
            "holidays": sorted(holidays_list, key=lambda item: item["date"]),
        }

    def _parse_year(self, year_param, project):
        if not year_param:
            return timezone.now().astimezone(project.timezone).year
        try:
            return int(year_param)
        except (TypeError, ValueError):
            raise OfficialHolidayRequestError(
                "Invalid 'year'. Use an integer like 2025.",
                status.HTTP_400_BAD_REQUEST,
            )


class UpdateOfficialHolidaysUseCase:
    def execute(self, sector_uuid, enabled_dates, disabled_dates):
        if not sector_uuid:
            raise OfficialHolidayRequestError(
                "Parameter 'sector' is required",
                status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(enabled_dates, list) or not isinstance(disabled_dates, list):
            raise OfficialHolidayRequestError(
                "enabled_holidays and disabled_holidays must be lists",
                status.HTTP_400_BAD_REQUEST,
            )

        try:
            sector = Sector.objects.get(uuid=sector_uuid)
        except Sector.DoesNotExist:
            raise OfficialHolidayRequestError(
                "Sector not found",
                status.HTTP_404_NOT_FOUND,
            )

        country_code = get_country_from_timezone(str(sector.project.timezone))
        all_dates = [self._parse_date_str(d) for d in enabled_dates + disabled_dates]
        years = {d.year for d in all_dates if d}
        official_by_year = {
            y: get_country_holidays(country_code, y) or {} for y in years
        }

        enabled_count, disabled_count, errors = 0, 0, []

        for date_str in enabled_dates:
            holiday_date = self._parse_date_str(date_str)
            if not holiday_date:
                errors.append(f"Invalid date format: {date_str}")
                continue
            name = official_by_year.get(holiday_date.year, {}).get(holiday_date, "")
            self._enable_holiday(sector, holiday_date, name)
            enabled_count += 1

        for date_str in disabled_dates:
            holiday_date = self._parse_date_str(date_str)
            if not holiday_date:
                errors.append(f"Invalid date format: {date_str}")
                continue
            if self._disable_holiday(sector, holiday_date):
                disabled_count += 1

        return {
            "enabled": enabled_count,
            "disabled": disabled_count,
            "errors": errors,
        }

    def _parse_date_str(self, date_str):
        if not isinstance(date_str, str) or not date_str:
            return None
        try:
            return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
        except ValueError:
            return None

    def _enable_holiday(self, sector, holiday_date, name):
        holiday = SectorHoliday.objects.filter(sector=sector, date=holiday_date).first()
        if holiday:
            self._update_existing_holiday(holiday, name)
            return

        SectorHoliday.objects.create(
            sector=sector,
            date=holiday_date,
            day_type=SectorHoliday.CLOSED,
            description=name,
            its_custom=False,
        )

    def _update_existing_holiday(self, holiday, name):
        changed = False
        if holiday.is_deleted:
            holiday.is_deleted = False
            changed = True
        if holiday.day_type != SectorHoliday.CLOSED:
            holiday.day_type = SectorHoliday.CLOSED
            changed = True
        if holiday.its_custom:
            holiday.its_custom = False
            changed = True
        if name and holiday.description != name:
            holiday.description = name
            changed = True
        if changed:
            holiday.save()

    def _disable_holiday(self, sector, holiday_date):
        holiday = SectorHoliday.objects.filter(sector=sector, date=holiday_date).first()
        if holiday and not holiday.is_deleted:
            holiday.is_deleted = True
            holiday.save(update_fields=["is_deleted"])
            return True
        return False


class ImportOfficialHolidaysUseCase:
    def execute(self, sector_uuid, year, selected_holidays):
        if not sector_uuid:
            raise OfficialHolidayRequestError(
                "Field 'sector' is required",
                status.HTTP_400_BAD_REQUEST,
            )

        try:
            sector = Sector.objects.get(uuid=sector_uuid)
        except Sector.DoesNotExist:
            raise OfficialHolidayRequestError(
                "Sector not found",
                status.HTTP_404_NOT_FOUND,
            )

        country_code = get_country_from_timezone(str(sector.project.timezone))
        official_holidays = get_country_holidays(country_code, int(year))

        created_holidays = []
        errors = []

        for holiday_date_str in selected_holidays:
            try:
                holiday_date = datetime.strptime(holiday_date_str, "%Y-%m-%d").date()

                if holiday_date not in official_holidays:
                    errors.append(f"Date {holiday_date_str} is not an official holiday")
                    continue

                if SectorHoliday.objects.filter(
                    sector=sector, date=holiday_date, is_deleted=False
                ).exists():
                    errors.append(f"Holiday for {holiday_date_str} already exists")
                    continue

                holiday = SectorHoliday.objects.create(
                    sector=sector,
                    date=holiday_date,
                    day_type=SectorHoliday.CLOSED,
                    description=official_holidays[holiday_date],
                )

                created_holidays.append(
                    {
                        "uuid": str(holiday.uuid),
                        "date": holiday_date_str,
                        "description": holiday.description,
                    }
                )
            except ValueError:
                errors.append(f"Invalid date format: {holiday_date_str}")
            except Exception as exc:
                errors.append(
                    f"Error creating holiday for {holiday_date_str}: {str(exc)}"
                )

        return {
            "created": len(created_holidays),
            "holidays": created_holidays,
            "errors": errors,
        }
