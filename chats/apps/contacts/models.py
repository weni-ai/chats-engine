from django.db import models
from django.utils.translation import gettext_lazy as _

from chats.core.models import BaseModel

Q = models.Q


class Contact(BaseModel):
    name = models.CharField(_("first name"), max_length=30, blank=True)
    email = models.EmailField(_("email"), unique=True, help_text=_("User email"))
    status = models.CharField(_("status"), max_length=30, blank=True)
    phone = models.CharField(_("phone"), max_length=30, blank=True)

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
        return self.rooms.filter(is_active=False).last()

    @property
    def tags(self):
        try:
            return self.last_room.tags
        except AttributeError:
            return None

    def can_retrieve(self, user, project) -> bool:
        filter_project_uuid = Q(queue__sector__project__uuid=project)
        is_sector_manager = Q(queue__sector__authorizations__permission__user=user)
        is_project_admin = Q(
            Q(queue__sector__project__permissions__user=user)
            & Q(queue__sector__project__permissions__role=2)
        )
        is_user_assigned_to_room = Q(user=user)
        check_admin_manager_agent_role_filter = Q(
            filter_project_uuid
            & (is_sector_manager | is_project_admin | is_user_assigned_to_room)
        )

        rooms_check = self.rooms.filter(
            check_admin_manager_agent_role_filter,
        ).exists()
        return rooms_check
