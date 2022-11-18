import json

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from chats.apps.msgs.models import Message as ChatMessage

from datetime import datetime
from dateutil.relativedelta import *

from chats.apps.api.v1.prometheus.metrics import(
    total_message,
    total_msgs_last_month,
    total_msgs_last_3_months,
    total_msgs_last_6_months,
    total_msgs_last_year,
)

now = datetime.now()
last_month = now + relativedelta(months=-1)
last_3_months = now + relativedelta(months=-3)
last_6_months = now + relativedelta(months=-6)
last_year = now + relativedelta(years=-1)

@receiver(post_save, sender=ChatMessage)
def send_websocket_message_notification(sender, instance, created, **kwargs):
    pass
    # if created:
    #     channel_layer = get_channel_layer()
    #     async_to_sync(channel_layer.group_send)(
    #         f"service_{instance.room.pk}",
    #         {"type": "room_messages", "message": json.dumps(instance)},
    #     )

@receiver([post_save, post_delete], sender=ChatMessage)
def msgs_metrics_sender(sender, instance, **kwargs):
   Metrics()

class Metrics():
    def __init__(self):
        metrics = [method for method in dir(self) if callable(getattr(self, method)) if not method.startswith('_') ]
        for method in metrics:
            getattr(self, method)()


    def send_metric_about_created_messages(self):
        message_count = ChatMessage.objects.all().count()
        total_message.labels("total_message").set(message_count)

    def metric_total_msgs_created_last_month(self):
        last_month_msgs_count = ChatMessage.objects.filter(created_on__range=[last_month,now]).count()
        total_msgs_last_month.labels("total_msgs_last_month").set(last_month_msgs_count)

    def metric_total_msgs_created_last_3_months(self):
        last_3_months_msgs_count = ChatMessage.objects.filter(created_on__range=[last_3_months,now]).count()
        total_msgs_last_3_months.labels("total_msgs_last_3_months").set(last_3_months_msgs_count)

    def metric_total_msgs_created_last_6_months(self):
        last_6_months_msgs_count = ChatMessage.objects.filter(created_on__range=[last_6_months,now]).count()
        total_msgs_last_6_months.labels("total_msgs_last_6_months").set(last_6_months_msgs_count)

    def metric_total_msgs_created_last_year(self):
        last_year_msgs_count = ChatMessage.objects.filter(created_on__range=[last_year,now]).count()
        total_msgs_last_year.labels("total_msgs_last_year").set(last_year_msgs_count)
