from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils.translation import gettext_lazy as _

from chats.core.models import BaseModel

Q = models.Q


class Contact(BaseModel):
    external_id = models.CharField(
        _("External ID"), max_length=200, blank=True, null=True
    )
    name = models.CharField(_("first name"), max_length=200, blank=True)
    email = models.EmailField(
        _("email"), unique=False, help_text=_("Contact email"), blank=True, null=True
    )
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
        return str(self.name)

    def get_linked_user(self, project):
        try:
            linked_user = self.linked_users.get(project=project)
            return linked_user
        except (ObjectDoesNotExist, AttributeError):
            return None

    @property
    def full_name(self):
        return self.name

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

    def last_room(self, request):
        """
        Return the last closed room.
        Filtered by the project or sector and user permission.
        This is used on the history endpoint
        """

        project = request.query_params.get("project")
        sector = request.query_params.get("sector")
        user = request.user
        filters = {
            "queue__sector__project__permissions__user": user,
            "queue__sector__project__uuid": project,
            "queue__sector__uuid": sector,
        }
        valid_filters = dict((k, v) for k, v in filters.items() if v is not None)

        return (
            self.rooms.order_by("created_on")
            .filter(is_active=False, **valid_filters)
            .last()
        )

    def tags_list(self, request):
        """
        Return the tags from the last closed room.
        Filtered by the project or sector and user permission.
        This is used on the history endpoint
        """

        try:
            return self.last_room(request).tags
        except AttributeError:
            return None

    def can_retrieve(self, user, project) -> bool:
        filter_project_uuid = Q(queue__sector__project__uuid=project)
        is_sector_manager = Q(queue__sector__authorizations__permission__user=user)
        is_project_admin = Q(
            Q(queue__sector__project__permissions__user=user)
            & Q(queue__sector__project__permissions__role=1)
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
