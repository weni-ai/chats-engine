from chats.apps.contacts.models import Contact
from django.db.models.signals import post_save, post_delete
from django.utils import timezone

from django.dispatch import receiver

from dateutil.relativedelta import relativedelta

from chats.apps.api.v1.prometheus.metrics import(
    chats_total_contacts, 
    chats_total_contacts_last_month,
    chats_total_contacts_last_3_months,
    chats_total_contacts_last_6_months,
    chats_total_contacts_last_1_year,
    chats_online_contacts, 
    chats_offline_contacts
)

@receiver([post_save, post_delete], sender=Contact)
def contacts_metrics_sender(sender, instance, **kwargs):
   Metrics()


class Metrics():
    def __init__(self):
        metrics = [method for method in dir(self) if callable(getattr(self, method)) if not method.startswith('_') ]
        for method in metrics:
            getattr(self, method)()

    def metric_total_contacts(self):
        contacts_count = Contact.objects.all().count()
        chats_total_contacts.labels("total_contacts").set(contacts_count)

    def metric_total_contacts_created_last_month(self):
        now = timezone.now()
        last_month = now + relativedelta(months=-1)

        contacts_count = Contact.objects.filter(created_on__gte=last_month).count()
        chats_total_contacts_last_month.labels("total_contacts_last_month").set(contacts_count)

    def metric_total_contacts_created_last_3_months(self):
        now = timezone.now()
        last_3_months = now + relativedelta(months=-3)

        contacts_count = Contact.objects.filter(created_on__gte=last_3_months).count()
        chats_total_contacts_last_3_months.labels("total_contacts_last_3_month").set(contacts_count)

    def metric_total_contacts_created_last_6_months(self):
        now = timezone.now()
        last_6_months = now + relativedelta(months=-6)

        contacts_count = Contact.objects.filter(created_on__gte=last_6_months).count()
        chats_total_contacts_last_6_months.labels("total_contacts_last_6_months").set(contacts_count)

    def metric_total_contacts_created_last_1_year(self):
        now = timezone.now()
        last_year = now + relativedelta(years=-1)

        contacts_count = Contact.objects.filter(created_on__gte=last_year).count()
        chats_total_contacts_last_1_year.labels("total_contacts_last_1_year").set(contacts_count)

    def metric_online_contacts(self):
        contacts_count = Contact.objects.filter(status="online").count()
        chats_online_contacts.labels("online_contacts").set(contacts_count)

    def metric_offline_contacts(self):
        contacts_count = Contact.objects.filter(status="offline").count()
        chats_offline_contacts.labels("offline_contacts").set(contacts_count)




