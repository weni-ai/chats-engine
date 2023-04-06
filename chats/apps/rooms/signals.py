from dateutil.relativedelta import relativedelta
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone

from chats.apps.api.v1.prometheus.metrics import (
    chats_closed_rooms, chats_opened_rooms, chats_total_rooms, chats_total_rooms_last_3_months,
    chats_total_rooms_last_6_months, chats_total_rooms_last_month, chats_total_rooms_last_year,
)
from chats.apps.rooms.models import Room


@receiver([post_save, post_delete], sender=Room)
def rooms_metrics_sender(sender, instance, **kwargs):
    Metrics()


class Metrics:
    def __init__(self):
        metrics = [
            method
            for method in dir(self)
            if callable(getattr(self, method))
            if not method.startswith("_")
        ]
        for method in metrics:
            getattr(self, method)()

    def metric_total_rooms(self):
        rooms_count = Room.objects.all().count()
        chats_total_rooms.labels("total_rooms").set(rooms_count)

    def metric_opened_rooms(self):
        open_rooms_count = Room.objects.filter(ended_at__isnull=True).count()
        chats_opened_rooms.labels("opened_rooms").set(open_rooms_count)

    def metric_closed_rooms(self):
        closed_rooms_count = Room.objects.filter(ended_at__isnull=False).count()
        chats_closed_rooms.labels("closed_rooms").set(closed_rooms_count)

    def metric_total_rooms_created_last_month(self):
        now = timezone.now()
        last_month = now + relativedelta(months=-1)

        last_month_rooms_count = Room.objects.filter(created_on__gte=last_month).count()
        chats_total_rooms_last_month.labels("total_rooms_last_month").set(
            last_month_rooms_count
        )

    def metric_total_rooms_created_last_3_months(self):
        now = timezone.now()
        last_3_months = now + relativedelta(months=-3)

        last_3_months_rooms_count = Room.objects.filter(
            created_on__gte=last_3_months
        ).count()
        chats_total_rooms_last_3_months.labels("total_rooms_last_3_months").set(
            last_3_months_rooms_count
        )

    def metric_total_rooms_created_last_6_months(self):
        now = timezone.now()
        last_6_months = now + relativedelta(months=-6)

        last_6_months_rooms_count = Room.objects.filter(
            created_on__gte=last_6_months
        ).count()
        chats_total_rooms_last_6_months.labels("total_rooms_last_6_months").set(
            last_6_months_rooms_count
        )

    def metric_total_rooms_created_last_year(self):
        now = timezone.now()
        last_year = now + relativedelta(years=-1)

        last_year_rooms_count = Room.objects.filter(created_on__gte=last_year).count()
        chats_total_rooms_last_year.labels("total_rooms_last_year").set(
            last_year_rooms_count
        )
