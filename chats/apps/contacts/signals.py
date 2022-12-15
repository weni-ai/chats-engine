from chats.apps.contacts.models import Contact
from django.db.models.signals import post_save, post_delete

from django.dispatch import receiver

from datetime import datetime
from dateutil.relativedelta import *

from chats.apps.api.v1.prometheus.metrics import(
    total_contacts, 
    total_contacts_last_month,
    total_contacts_last_3_months,
    total_contacts_last_6_months,
    total_contacts_last_1_year,
    online_contacts, 
    offline_contacts
)

now = datetime.now()
last_month = now + relativedelta(months=-1)
last_3_months = now + relativedelta(months=-3)
last_6_months = now + relativedelta(months=-6)
last_year = now + relativedelta(years=-1)

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
        total_contacts.labels("total_contacts").set(contacts_count)

    def metric_total_contacts_created_last_month(self):
        contacts_count = Contact.objects.filter(created_on__range=[last_month,now]).count()
        total_contacts_last_month.labels("total_contacts_last_month").set(contacts_count)

    def metric_total_contacts_created_last_3_months(self):
        contacts_count = Contact.objects.filter(created_on__range=[last_3_months,now]).count()
        total_contacts_last_3_months.labels("total_contacts_last_3_month").set(contacts_count)

    def metric_total_contacts_created_last_6_months(self):
        contacts_count = Contact.objects.filter(created_on__range=[last_6_months,now]).count()
        total_contacts_last_6_months.labels("total_contacts_last_6_months").set(contacts_count)

    def metric_total_contacts_created_last_1_year(self):
        contacts_count = Contact.objects.filter(created_on__range=[last_year,now]).count()
        total_contacts_last_1_year.labels("total_contacts_last_1_year").set(contacts_count)

    def metric_online_contacts(self):
        contacts_count = Contact.objects.filter(status="online").count()
        online_contacts.labels("online_contacts").set(contacts_count)

    def metric_offline_contacts(self):
        contacts_count = Contact.objects.filter(status="offline").count()
        offline_contacts.labels("offline_contacts").set(contacts_count)




