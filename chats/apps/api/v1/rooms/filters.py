from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters

from chats.apps.rooms.models import Room
from rest_framework.filters import OrderingFilter


class RoomFilter(filters.FilterSet):
    class Meta:
        model = Room
        fields = ["queue", "is_active"]

    project = filters.CharFilter(
        field_name="project",
        required=True,
        method="filter_project",
        help_text=_("Project's UUID"),
    )

    is_active = filters.BooleanFilter(
        field_name="is_active",
        required=False,
        method="filter_is_active",
        help_text=_("Is active?"),
    )

    def filter_project(self, queryset, name, value):
        try:
            project_permission = self.request.user.project_permissions.get(
                project__uuid=value
            )
        except ObjectDoesNotExist:
            return queryset.none()
        if project_permission.is_admin:
            user_filter = Q(user=self.request.user) | Q(user__isnull=True)
            return queryset.filter(
                user_filter, is_active=True, queue__in=project_permission.queue_ids
            )
        user_project = Q(user=self.request.user) & Q(queue__sector__project__uuid=value)
        queue_filter = Q(user__isnull=True) & Q(queue__in=project_permission.queue_ids)
        ff = user_project | queue_filter
        queryset = queryset.filter(
            ff,
            is_active=True,
        )
        return queryset

    def filter_is_active(self, queryset, name, value):
        return queryset.filter(is_active=value)


class CustomOrderingFilter(OrderingFilter):
    def get_valid_fields(self, queryset, view, context={}):
        valid_fields = getattr(view, "ordering_fields", self.ordering_fields)

        if valid_fields is None:
            # Default to allowing filtering on serializer fields
            return self.get_default_valid_fields(queryset, view, context)

        elif valid_fields == "__all__":
            # View explicitly allows filtering on any model field
            valid_fields = [
                (field.name, field.verbose_name)
                for field in queryset.model._meta.fields
            ]
            valid_fields += [
                (field.related_name, field.related_name)
                for key, field in queryset.model._meta.fields_map.items()
            ]
            valid_fields += [
                (key, key.title().split("__")) for key in queryset.query.annotations
            ]
        else:
            valid_fields = [
                (item, item) if isinstance(item, str) else item for item in valid_fields
            ]
        return valid_fields

    def remove_invalid_fields(self, queryset, fields, view, request):
        valid_fields = [
            item[0]
            for item in self.get_valid_fields(queryset, view, {"request": request})
        ]

        def term_valid(term):
            if term.startswith("-"):
                term = term[1:]
                if "__" in term:
                    term = term.split("__")[0]
            return term in valid_fields

        qs = [term for term in fields if term_valid(term)]
        return qs
