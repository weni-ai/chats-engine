import logging
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from chats.apps.accounts.models import User
from chats.apps.sectors.services import AutomaticMessagesService
from chats.celery import app

logger = logging.getLogger(__name__)

BATCH_SIZE = 100


@app.task
def send_automatic_message(
    room_uuid: UUID, message: str, user_id: int, check_ticket: bool = False
):
    """
    Send an automatic message to a room.
    """
    from chats.apps.rooms.models import Room

    room = Room.objects.get(uuid=room_uuid)
    user = User.objects.get(id=user_id)

    AutomaticMessagesService().send_automatic_message(room, message, user, check_ticket)


@app.task
def create_official_holidays_for_all_sectors(year: int = None):
    """
    Create official holidays for all active sectors based on project timezone.
    Processes sectors in batches for better performance.
    """
    from chats.apps.sectors.models import Sector, SectorHoliday
    from chats.apps.sectors.utils import get_country_from_timezone, get_country_holidays

    if year is None:
        year = timezone.now().year

    sectors = Sector.objects.filter(is_deleted=False).select_related("project")
    total_sectors = sectors.count()

    logger.info(f"Starting holiday creation for year {year}. Total sectors: {total_sectors}")

    created_count = 0
    skipped_count = 0
    error_count = 0
    processed_sectors = 0

    for offset in range(0, total_sectors, BATCH_SIZE):
        batch = sectors[offset : offset + BATCH_SIZE]

        for sector in batch:
            processed_sectors += 1
            try:
                project_timezone = (
                    str(sector.project.timezone) if sector.project.timezone else None
                )
                country_code = get_country_from_timezone(project_timezone)

                if not country_code:
                    logger.warning(
                        f"Sector {sector.uuid}: No country code for timezone {project_timezone}"
                    )
                    skipped_count += 1
                    continue

                official_holidays = get_country_holidays(country_code, year)

                if not official_holidays:
                    logger.warning(
                        f"Sector {sector.uuid}: No holidays found for country {country_code}"
                    )
                    skipped_count += 1
                    continue

                existing_dates = set(
                    SectorHoliday.objects.filter(
                        sector=sector, date__year=year, is_deleted=False
                    ).values_list("date", flat=True)
                )

                holidays_to_create = []
                for holiday_date, holiday_name in official_holidays.items():
                    if holiday_date not in existing_dates:
                        holidays_to_create.append(
                            SectorHoliday(
                                sector=sector,
                                date=holiday_date,
                                day_type=SectorHoliday.CLOSED,
                                description=holiday_name,
                                its_custom=False,
                            )
                        )

                if holidays_to_create:
                    with transaction.atomic():
                        SectorHoliday.objects.bulk_create(holidays_to_create)
                    created_count += len(holidays_to_create)
                    logger.info(
                        f"Sector {sector.uuid}: Created {len(holidays_to_create)} holidays"
                    )

            except Exception as e:
                error_count += 1
                logger.error(f"Sector {sector.uuid}: Error creating holidays - {str(e)}")

        logger.info(f"Processed {processed_sectors}/{total_sectors} sectors")

    logger.info(
        f"Holiday creation completed for year {year}. "
        f"Created: {created_count}, Skipped: {skipped_count}, Errors: {error_count}"
    )

    return {
        "year": year,
        "total_sectors": total_sectors,
        "holidays_created": created_count,
        "sectors_skipped": skipped_count,
        "errors": error_count,
    }
