from django.db import models
from django.utils.translation import gettext_lazy as _

from chats.core.models import BaseModel


class Contact(BaseModel):
    name = models.CharField(_("first name"), max_length=30, blank=True)
    email = models.EmailField(_("email"), unique=True, help_text=_("User email"))
    status = models.CharField(_("status"), max_length=30, blank=True)
    custom_fields = models.JSONField(
        _("custom fields"),
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = _("Contact")
        verbose_name_plural = _("Contacts")

    def __str__(self):
        return self.email

    @property
    def last_agent_name(self):
        try:
            return self.rooms.last().user.name
        except AttributeError:
            return ""

    @property
    def serialized_ws_data(self):
        from chats.apps.api.v1.contacts.serializers import ContactWSSerializer

        return ContactWSSerializer(self).data

    @property
    def last_room(self):
        return self.rooms.filter(is_active=True).last()

    @property
    def tags(self):
        return self.last_room.tags
