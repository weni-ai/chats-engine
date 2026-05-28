from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from weni.feature_flags.shortcuts import (
    is_feature_active_for_attributes,
)

from chats.apps.api.v1.accounts.serializers import UserSerializer
from chats.apps.projects.models import Project
from chats.apps.sectors.constants import get_default_inactivity_timeout
from chats.apps.sectors.models import (
    Sector,
    SectorAuthorization,
    SectorHoliday,
    SectorTag,
)
from chats.core.serializers import AuditableModelSerializer
from chats.apps.projects.models import Project

User = get_user_model()


def validate_is_csat_enabled(project: Project, value: bool, context: dict) -> bool:
    """
    Validate if the CSAT feature is enabled for the sector.
    """
    request = context.get("request")
    user = getattr(request, "user", None)
    project = project

    if value is True and not is_feature_active(
        settings.CSAT_FEATURE_FLAG_KEY, user.email, str(project.uuid)
    ):
        raise serializers.ValidationError(
            {
                "is_csat_enabled": [
                    _("The CSAT feature is not available for this sector")
                ]
            },
            code="csat_feature_flag_is_off",
        )
    return value


def _apply_sector_config_defaults(instance: Sector, data: dict) -> dict:
    config = data.get("config") or {}
    if isinstance(config, dict):
        if instance:
            config.setdefault(
                "can_close_chats_in_queue", instance.can_close_chats_in_queue
            )
        else:
            config.setdefault("can_close_chats_in_queue", False)
    data["config"] = config
    return data


def validate_custom_csat_flow_uuid(project: Project, value, current_value=None):
    """
    Validate if the custom CSAT flow feature is enabled for the sector.
    When the feature is off, only allow clearing an already-set value.
    """
    if is_feature_active_for_attributes(
        settings.CUSTOM_CSAT_FLOW_FEATURE_FLAG_KEY,
        {"projectUUID": str(project.uuid)},
    ):
        return value

    if current_value is not None and not value:
        return value

    if value:
        raise serializers.ValidationError(
            {
                "custom_csat_flow_uuid": [
                    _("The custom CSAT flow feature is not available for this sector")
                ]
            },
            code="custom_csat_flow_feature_flag_is_off",
        )

    return value


class SectorAutomaticMessageSerializer(serializers.ModelSerializer):
    is_active = serializers.BooleanField(source="is_automatic_message_active")
    text = serializers.CharField(source="automatic_message_text")

    class Meta:
        model = Sector
        fields = ["is_active", "text"]


class SectorInactivityTimeoutSerializer(serializers.Serializer):
    """
    Validates the shape of the `Sector.inactivity_timeout` JSON field.

    Time fields are stored in seconds.
    """

    is_message_timeout_enabled = serializers.BooleanField()
    message_timeout_text = serializers.CharField(allow_blank=True, allow_null=True)
    message_timeout_time = serializers.IntegerField(min_value=1, allow_null=True)
    is_close_room_enabled = serializers.BooleanField()
    close_room_message_text = serializers.CharField(allow_blank=True, allow_null=True)
    close_room_timeout_time = serializers.IntegerField(min_value=1, allow_null=True)

    def validate(self, attrs: dict) -> dict:
        is_message_timeout_enabled = attrs.get("is_message_timeout_enabled", False)
        is_close_room_enabled = attrs.get("is_close_room_enabled", False)

        if is_close_room_enabled and not is_message_timeout_enabled:
            raise serializers.ValidationError(
                {
                    "is_close_room_enabled": _(
                        "Automatic closure can only be enabled if the inactivity "
                        "warning is also enabled."
                    )
                }
            )

        if is_message_timeout_enabled and not attrs.get("message_timeout_time"):
            raise serializers.ValidationError(
                {
                    "message_timeout_time": _(
                        "Provide a value greater than zero when the inactivity "
                        "warning is enabled."
                    )
                }
            )

        if is_close_room_enabled and not attrs.get("close_room_timeout_time"):
            raise serializers.ValidationError(
                {
                    "close_room_timeout_time": _(
                        "Provide a value greater than zero when the automatic "
                        "closure is enabled."
                    )
                }
            )

        return attrs


def _serialize_inactivity_timeout(instance: Sector) -> dict:
    """
    Returns the sector's `inactivity_timeout` value, falling back to the
    default shape when the sector has not configured the feature yet.
    """
    if instance and instance.inactivity_timeout:
        return instance.inactivity_timeout
    return get_default_inactivity_timeout()


class SectorAutomaticMessageQueueSerializer(serializers.ModelSerializer):
    is_active = serializers.BooleanField(source="is_automatic_message_queue_active")
    text = serializers.CharField(
        source="automatic_message_queue_text", allow_blank=True, allow_null=True
    )

    class Meta:
        model = Sector
        fields = ["is_active", "text"]


class SectorSerializer(AuditableModelSerializer):
    automatic_message = serializers.JSONField(required=False)
    inactivity_timeout = serializers.JSONField(required=False, allow_null=True)
    automatic_message_queue = serializers.JSONField(required=False)
    is_csat_enabled = serializers.BooleanField(required=False, allow_null=False)
    custom_csat_flow_uuid = serializers.UUIDField(required=False, allow_null=True)

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
            "inactivity_timeout",
            "automatic_message_queue",
            "is_csat_enabled",
            "required_tags",
            "secondary_project",
            "custom_csat_flow_uuid",
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
            data.pop("automatic_message")

            data["is_automatic_message_active"] = automatic_message.get("is_active")
            data["automatic_message_text"] = automatic_message.get("text")

        if "inactivity_timeout" in data:
            inactivity_timeout = data.get("inactivity_timeout")
            if inactivity_timeout is None:
                data["inactivity_timeout"] = None
            else:
                nested = SectorInactivityTimeoutSerializer(data=inactivity_timeout)
                nested.is_valid(raise_exception=True)
                data["inactivity_timeout"] = nested.validated_data

        automatic_message_queue = data.get("automatic_message_queue")

        if automatic_message_queue is not None:
            data.pop("automatic_message_queue")

            is_active = automatic_message_queue.get("is_active")
            text = automatic_message_queue.get("text")

            if is_active and not (text and text.strip()):
                raise serializers.ValidationError(
                    {
                        "automatic_message_queue": _(
                            "Text is required when automatic queue message "
                            "is active."
                        )
                    },
                    code="automatic_message_queue_text_required_when_active",
                )

            data["is_automatic_message_queue_active"] = is_active
            data["automatic_message_queue_text"] = text

        project = self.instance.project if self.instance else data.get("project")

        if project and "custom_csat_flow_uuid" in data:
            validate_custom_csat_flow_uuid(
                project,
                data.get("custom_csat_flow_uuid"),
                current_value=(
                    getattr(self.instance, "custom_csat_flow_uuid", None)
                    if self.instance
                    else None
                ),
            )

        config = data.get("config", {})
        if "secondary_project" in config:
            secondary_project_value = config.get("secondary_project")
            if isinstance(secondary_project_value, str):
                data["secondary_project"] = {"uuid": secondary_project_value}
            else:
                data["secondary_project"] = secondary_project_value

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
        data["inactivity_timeout"] = _serialize_inactivity_timeout(instance)
        data["automatic_message_queue"] = SectorAutomaticMessageQueueSerializer(
            instance
        ).data
        data = _apply_sector_config_defaults(instance, data)

        return data


class SectorUpdateSerializer(AuditableModelSerializer):
    automatic_message = serializers.JSONField(required=False)
    inactivity_timeout = serializers.JSONField(required=False, allow_null=True)
    automatic_message_queue = serializers.JSONField(required=False)
    is_csat_enabled = serializers.BooleanField(required=False, allow_null=False)
    custom_csat_flow_uuid = serializers.UUIDField(required=False, allow_null=True)

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
            "inactivity_timeout",
            "automatic_message_queue",
            "is_csat_enabled",
            "required_tags",
            "secondary_project",
            "custom_csat_flow_uuid",
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
        automatic_message = attrs.get("automatic_message", None)

        if automatic_message is not None:
            new_is_automatic_message_active = automatic_message.get("is_active")

            attrs.pop("automatic_message")
            attrs["is_automatic_message_active"] = new_is_automatic_message_active
            attrs["automatic_message_text"] = automatic_message.get("text")

        if "inactivity_timeout" in attrs:
            inactivity_timeout = attrs.get("inactivity_timeout")
            if inactivity_timeout is None:
                attrs["inactivity_timeout"] = None
            else:
                nested = SectorInactivityTimeoutSerializer(data=inactivity_timeout)
                nested.is_valid(raise_exception=True)
                attrs["inactivity_timeout"] = nested.validated_data

        automatic_message_queue = attrs.get("automatic_message_queue", None)

        if automatic_message_queue is not None:
            attrs.pop("automatic_message_queue")

            is_active = automatic_message_queue.get("is_active")

            if "text" in automatic_message_queue:
                text = automatic_message_queue.get("text")
            elif self.instance is not None:
                text = self.instance.automatic_message_queue_text
            else:
                text = None

            if is_active and not (text and text.strip()):
                raise serializers.ValidationError(
                    {
                        "automatic_message_queue": _(
                            "Text is required when automatic queue message "
                            "is active."
                        )
                    },
                    code="automatic_message_queue_text_required_when_active",
                )

            attrs["is_automatic_message_queue_active"] = is_active
            attrs["automatic_message_queue_text"] = text

        project = self.instance.project

        if "custom_csat_flow_uuid" in attrs:
            validate_custom_csat_flow_uuid(
                project,
                attrs.get("custom_csat_flow_uuid"),
                current_value=self.instance.custom_csat_flow_uuid,
            )

        config = attrs.get("config", {})
        if "secondary_project" in config:
            secondary_project_value = config.get("secondary_project")
            if isinstance(secondary_project_value, str):
                attrs["secondary_project"] = {"uuid": secondary_project_value}
            else:
                attrs["secondary_project"] = secondary_project_value

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
        data["inactivity_timeout"] = _serialize_inactivity_timeout(instance)
        data["automatic_message_queue"] = SectorAutomaticMessageQueueSerializer(
            instance
        ).data
        data = _apply_sector_config_defaults(instance, data)

        return data


class SectorReadOnlyListSerializer(serializers.ModelSerializer):
    agents = serializers.SerializerMethodField()
    contacts = serializers.SerializerMethodField()
    has_group_sector = serializers.SerializerMethodField()
    automatic_message = serializers.SerializerMethodField()
    inactivity_timeout = serializers.SerializerMethodField()
    automatic_message_queue = serializers.SerializerMethodField()

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
            "inactivity_timeout",
            "automatic_message_queue",
            "is_csat_enabled",
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

    def get_inactivity_timeout(self, sector: Sector):
        return _serialize_inactivity_timeout(sector)

    def get_automatic_message_queue(self, sector: Sector):
        return SectorAutomaticMessageQueueSerializer(sector).data


class SectorReadOnlyRetrieveSerializer(serializers.ModelSerializer):
    automatic_message = serializers.SerializerMethodField()
    inactivity_timeout = serializers.SerializerMethodField()
    automatic_message_queue = serializers.SerializerMethodField()

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
            "inactivity_timeout",
            "automatic_message_queue",
            "is_csat_enabled",
            "required_tags",
            "custom_csat_flow_uuid",
        ]

    def get_automatic_message(self, sector: Sector):
        return SectorAutomaticMessageSerializer(sector).data

    def get_inactivity_timeout(self, sector: Sector):
        return _serialize_inactivity_timeout(sector)

    def get_automatic_message_queue(self, sector: Sector):
        return SectorAutomaticMessageQueueSerializer(sector).data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        return _apply_sector_config_defaults(instance, data)


class SectorWSSerializer(serializers.ModelSerializer):
    """
    used to serialize data for the websocket connection
    TODO: Add a field checking if the sector can receive new rooms based on work_start and work_end
    """

    class Meta:
        model = Sector
        fields = "__all__"


# Sector Authorization Serializers


class SectorAuthorizationSerializer(AuditableModelSerializer):
    class Meta:
        model = SectorAuthorization
        fields = "__all__"

    def _get_audit_project(self):
        if self.instance is not None:
            return self.instance.sector.project
        sector = (self.validated_data or {}).get("sector")
        return sector.project if sector else None


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


class SectorTagSerializer(AuditableModelSerializer):
    class Meta:
        model = SectorTag
        fields = "__all__"
        extra_kwargs = {"sector": {"required": False}}

    def _get_audit_project(self):
        if self.instance is not None:
            return self.instance.sector.project
        sector = (self.validated_data or {}).get("sector")
        return sector.project if sector else None

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


class SectorHolidaySerializer(AuditableModelSerializer):
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

    def _get_audit_project(self):
        if self.instance is not None:
            return self.instance.sector.project
        sector = (self.validated_data or {}).get("sector")
        return sector.project if sector else None

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
