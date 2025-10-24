from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from chats.apps.api.v1.accounts.serializers import UserSerializer
from chats.apps.sectors.models import (
    Sector,
    SectorAuthorization,
    SectorHoliday,
    SectorTag,
)
from chats.apps.feature_flags.utils import is_feature_active

User = get_user_model()


class SectorAutomaticMessageSerializer(serializers.ModelSerializer):
    is_active = serializers.BooleanField(source="is_automatic_message_active")
    text = serializers.CharField(source="automatic_message_text")

    class Meta:
        model = Sector
        fields = ["is_active", "text"]


class SectorSerializer(serializers.ModelSerializer):
    automatic_message = serializers.JSONField(required=False)

    class Meta:
        model = Sector
        fields = [
            "uuid",
            "name",
            "can_edit_custom_fields",
            "can_trigger_flows",
            "config",
            "project",
            "rooms_limit",
            "sign_messages",
            "work_start",
            "work_end",
            "open_offline",
            "can_edit_custom_fields",
            "working_day",
            "automatic_message",
            "required_tags",
            "secondary_project",
        ]
        extra_kwargs = {
            "work_start": {"required": False, "allow_null": True},
            "work_end": {"required": False, "allow_null": True},
        }

    def validate(self, data):
        """
        Check if the work_end date its greater than work_start date.
        """
        start = data.get(
            "work_start",
            getattr(self.instance, "work_start", None) if self.instance else None,
        )
        end = data.get(
            "work_end",
            getattr(self.instance, "work_end", None) if self.instance else None,
        )
        if start is not None and end is not None:
            if end <= start:
                raise serializers.ValidationError(
                    {"detail": _("work_end date must be greater than work_start date.")}
                )

        automatic_message = data.get("automatic_message")

        if automatic_message:
            if automatic_message.get("is_active", False) and not is_feature_active(
                settings.AUTOMATIC_MESSAGE_FEATURE_FLAG_KEY,
                self.context["request"].user,
                data.get("project"),
            ):
                raise serializers.ValidationError(
                    {
                        "is_automatic_message_active": [
                            _("This feature is not available for this project.")
                        ]
                    },
                    code="automatic_message_feature_flag_is_not_active",
                )

            data.pop("automatic_message")

            data["is_automatic_message_active"] = automatic_message.get("is_active")
            data["automatic_message_text"] = automatic_message.get("text")

        config = data.get("config", {})
        if config and "secondary_project" in config:
            secondary_project_value = config.pop("secondary_project")
            if isinstance(secondary_project_value, str):
                data["secondary_project"] = {"uuid": secondary_project_value}
            else:
                data["secondary_project"] = secondary_project_value
            data["config"] = config

        return data

    def validate_required_tags(self, value) -> bool:
        """
        Check if the sector has at least one tag to require tags.
        """

        if value is True:
            if not self.instance:
                # For now, tags are created after the sector is created
                # This may change in the future
                raise serializers.ValidationError(
                    [_("Sector must have at least one tag to require tags.")],
                    code="sector_must_have_at_least_one_tag_to_require_tags",
                )

            if not self.instance.tags.exists():
                raise serializers.ValidationError(
                    [_("Sector must have at least one tag to require tags.")],
                    code="sector_must_have_at_least_one_tag_to_require_tags",
                )

        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["automatic_message"] = SectorAutomaticMessageSerializer(instance).data

        return data


class SectorUpdateSerializer(serializers.ModelSerializer):
    automatic_message = serializers.JSONField(required=False)

    class Meta:
        model = Sector
        fields = [
            "name",
            "rooms_limit",
            "work_start",
            "work_end",
            "is_deleted",
            "can_trigger_flows",
            "sign_messages",
            "can_edit_custom_fields",
            "config",
            "automatic_message",
            "required_tags",
            "secondary_project",
        ]
        extra_kwargs = {field: {"required": False} for field in fields}

    def update(self, instance, validated_data):
        config = validated_data.pop("config", None)
        sector = super().update(instance, validated_data)

        if config is not None:
            sector.config = sector.config or {}
            sector.config.update(config)
            sector.save(update_fields=["config"])

        return sector

    def validate(self, attrs: dict):
        project = self.instance.project

        automatic_message = attrs.get("automatic_message", None)

        if automatic_message is not None:
            current_is_automatic_message_active = (
                self.instance.is_automatic_message_active
            )
            new_is_automatic_message_active = automatic_message.get("is_active")

            if (
                current_is_automatic_message_active != new_is_automatic_message_active
                and not is_feature_active(
                    settings.AUTOMATIC_MESSAGE_FEATURE_FLAG_KEY,
                    self.context["request"].user,
                    project,
                )
            ):

                raise serializers.ValidationError(
                    {
                        "is_automatic_message_active": [
                            _("This feature is not available for this project.")
                        ]
                    },
                    code="automatic_message_feature_flag_is_not_active",
                )

            attrs.pop("automatic_message")
            attrs["is_automatic_message_active"] = new_is_automatic_message_active
            attrs["automatic_message_text"] = automatic_message.get("text")

        config = attrs.get("config", {})
        if config and "secondary_project" in config:
            secondary_project_value = config.pop("secondary_project")
            if isinstance(secondary_project_value, str):
                attrs["secondary_project"] = {"uuid": secondary_project_value}
            else:
                attrs["secondary_project"] = secondary_project_value
            attrs["config"] = config

        return attrs

    def validate_required_tags(self, value) -> bool:
        """
        Check if the sector has at least one tag to require tags.
        """
        if value is True and not self.instance.tags.exists():
            raise serializers.ValidationError(
                [_("Sector must have at least one tag to require tags.")],
                code="sector_must_have_at_least_one_tag_to_require_tags",
            )

        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)

        data["automatic_message"] = SectorAutomaticMessageSerializer(instance).data

        return data


class SectorReadOnlyListSerializer(serializers.ModelSerializer):
    agents = serializers.SerializerMethodField()
    contacts = serializers.SerializerMethodField()
    has_group_sector = serializers.SerializerMethodField()
    automatic_message = serializers.SerializerMethodField()

    class Meta:
        model = Sector
        fields = [
            "uuid",
            "name",
            "agents",
            "contacts",
            "can_trigger_flows",
            "created_on",
            "has_group_sector",
            "automatic_message",
            "required_tags",
        ]

    def get_agents(self, sector: Sector):
        return sector.agent_count

    def get_contacts(self, sector: Sector):
        return sector.contact_count

    def get_has_group_sector(self, sector: Sector):
        return sector.sector_group_sectors.exists()

    def get_automatic_message(self, sector: Sector):
        return SectorAutomaticMessageSerializer(sector).data


class SectorReadOnlyRetrieveSerializer(serializers.ModelSerializer):
    automatic_message = serializers.SerializerMethodField()

    class Meta:
        model = Sector
        fields = [
            "uuid",
            "name",
            "work_start",
            "work_end",
            "rooms_limit",
            "can_trigger_flows",
            "sign_messages",
            "can_edit_custom_fields",
            "config",
            "automatic_message",
            "required_tags",
        ]

    def get_automatic_message(self, sector: Sector):
        return SectorAutomaticMessageSerializer(sector).data


class SectorWSSerializer(serializers.ModelSerializer):
    """
    used to serialize data for the websocket connection
    TODO: Add a field checking if the sector can receive new rooms based on work_start and work_end
    """

    class Meta:
        model = Sector
        fields = "__all__"


# Sector Authorization Serializers


class SectorAuthorizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SectorAuthorization
        fields = "__all__"


class SectorAuthorizationReadOnlySerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = SectorAuthorization
        fields = [
            "uuid",
            "sector",
            "role",
            "user",
        ]

    def get_user(self, auth):
        return UserSerializer(auth.permission.user).data


class SectorAuthorizationWSSerializer(serializers.ModelSerializer):
    class Meta:
        model = SectorAuthorization
        fields = "__all__"


# Sector Tags Serializer


class SectorTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = SectorTag
        fields = "__all__"
        extra_kwargs = {"sector": {"required": False}}

    def validate(self, data):
        """
        Check if tag already exist in sector.
        """
        if self.instance:
            if SectorTag.objects.filter(
                sector=self.instance.sector, name=data["name"]
            ).exists():
                raise serializers.ValidationError(
                    {"detail": _("This tag already exists.")}
                )
        else:
            if SectorTag.objects.filter(
                name=data["name"], sector=data["sector"]
            ).exists():
                raise serializers.ValidationError(
                    {"detail": _("This tag already exists.")}
                )
        return data


class DetailSectorTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = SectorTag
        exclude = [
            "sector",
        ]


class TagSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = SectorTag
        fields = ["uuid", "name", "is_deleted"]

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if instance.is_deleted:
            name = data.get("name").split("_is_deleted_")[0]
            data["name"] = f"{name}"

        return data


class SectorAgentsSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "photo_url",
            "language",
        ]


class SectorHolidaySerializer(serializers.ModelSerializer):
    """
    Serializer to manage configurable holidays and special days by sector
    """

    class Meta:
        model = SectorHoliday
        fields = [
            "uuid",
            "sector",
            "date",
            "date_end",
            "day_type",
            "start_time",
            "end_time",
            "description",
            "its_custom",
            "repeat",
            "created_on",
            "modified_on",
            "its_custom",
        ]
        read_only_fields = ["uuid", "created_on", "modified_on"]

    def validate(self, data):
        """
        Custom validations to ensure data consistency
        """
        day_type = data.get("day_type")
        start_time = data.get("start_time")
        end_time = data.get("end_time")

        if day_type == SectorHoliday.CLOSED:
            if start_time is not None or end_time is not None:
                raise serializers.ValidationError(
                    {"detail": _("Closed days should not have start_time or end_time")}
                )

        elif day_type == SectorHoliday.CUSTOM_HOURS:
            if start_time is None or end_time is None:
                raise serializers.ValidationError(
                    {
                        "detail": _(
                            "Custom hours days must have both start_time and end_time"
                        )
                    }
                )
            if start_time >= end_time:
                raise serializers.ValidationError(
                    {"detail": _("End time must be greater than start time")}
                )

        return data

    def to_representation(self, instance):
        """
        Renderiza `date` como objeto {start, end} quando `date_end` existir,
        senão string 'YYYY-MM-DD'.
        """
        data = super().to_representation(instance)
        start = instance.date.strftime("%Y-%m-%d")
        if instance.date_end:
            end = instance.date_end.strftime("%Y-%m-%d")
            data["date"] = {"start": start, "end": end}
        else:
            data["date"] = start
        data.pop("date_end", None)
        return data


class SectorHolidayListSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para listagem de holidays
    """

    class Meta:
        model = SectorHoliday
        fields = [
            "uuid",
            "date",
            "date_end",
            "day_type",
            "start_time",
            "end_time",
            "description",
            "its_custom",
            "repeat",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        start = instance.date.strftime("%Y-%m-%d")
        if instance.date_end:
            end = instance.date_end.strftime("%Y-%m-%d")
            data["date"] = {"start": start, "end": end}
        else:
            data["date"] = start
        data.pop("date_end", None)
        return data
