from django.contrib import admin

from chats.apps.queues.models import Queue, QueueAuthorization

# Register your models here.

admin.site.register(Queue)
admin.site.register(QueueAuthorization)
