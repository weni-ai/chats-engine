from django.contrib import admin

from chats.apps.msgs.models import Message, MessageMedia

# Register your models here.

admin.site.register(Message)
admin.site.register(MessageMedia)
