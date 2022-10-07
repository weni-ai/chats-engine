from django.contrib import admin

from chats.apps.sectors.models import Sector, SectorAuthorization, SectorTag

# Register your models here.

admin.site.register(Sector)
admin.site.register(SectorAuthorization)
admin.site.register(SectorTag)
