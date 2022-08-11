from django.contrib import admin
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.sectors.models import Sector, SectorAuthorization
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.accounts.models import User

# Register your models here.
admin.site.register(User)
admin.site.register(Project)
admin.site.register(ProjectPermission)
admin.site.register(Sector)
admin.site.register(SectorAuthorization)
admin.site.register(Queue)
admin.site.register(QueueAuthorization)

