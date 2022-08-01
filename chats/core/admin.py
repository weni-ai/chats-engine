import imp
from django.contrib import admin
from chats.apps.projects.models import Project
from chats.apps.sectors.models import Sector, SectorAuthorization
from chats.apps.sectorqueue.models import SectorQueue, SectorQueueAuthorization
from chats.apps.accounts.models import User

# Register your models here.
admin.site.register(User)
admin.site.register(Project)
admin.site.register(Sector)
admin.site.register(SectorAuthorization)
admin.site.register(SectorQueue)
admin.site.register(SectorQueueAuthorization)

