from chats.apps.queues.models import QueueAuthorization

from django.db.models.signals import post_save, post_delete

from django.dispatch import receiver

from datetime import datetime
from dateutil.relativedelta import *

from chats.apps.api.v1.prometheus.metrics import(
    total_agents,
    total_agents_last_month,
    total_agents_last_3_months,
    total_agents_last_6_months,
    total_agents_last_year
)

now = datetime.now()
last_month = now + relativedelta(months=-1)
last_3_months = now + relativedelta(months=-3)
last_6_months = now + relativedelta(months=-6)
last_year = now + relativedelta(years=-1)

@receiver([post_save, post_delete], sender=QueueAuthorization)
def queueauthorization_metrics_sender(sender, instance, **kwargs):
   Metrics()


class Metrics():
    def __init__(self):
        metrics = [method for method in dir(self) if callable(getattr(self, method)) if not method.startswith('_') ]
        for method in metrics:
            getattr(self, method)()

    def metric_about_created_agents(self):
        agent_authorization_count = QueueAuthorization.objects.all().count()
        total_agents.labels("total_agents").set(agent_authorization_count)

    def metric_total_agents_created_last_month(self):
        last_month_agents_count = QueueAuthorization.objects.filter(created_on__range=[last_month,now]).count()
        total_agents_last_month.labels("total_agents_last_month").set(last_month_agents_count)

    def metric_total_agents_created_last_3_months(self):
        last_3_months_agents_count = QueueAuthorization.objects.filter(created_on__range=[last_3_months,now]).count()
        total_agents_last_3_months.labels("total_agents_last_3_months").set(last_3_months_agents_count)

    def metric_total_agents_created_last_3_months(self):
        last_6_months_agents_count = QueueAuthorization.objects.filter(created_on__range=[last_6_months,now]).count()
        total_agents_last_6_months.labels("total_agents_last_6_months").set(last_6_months_agents_count)

    def metric_total_agents_created_last_year(self):
        last_year_agents_count = QueueAuthorization.objects.filter(created_on__range=[last_year,now]).count()
        total_agents_last_year.labels("total_agents_last_year").set(last_year_agents_count)
