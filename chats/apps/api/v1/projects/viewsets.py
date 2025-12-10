import json
import logging

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction
from django.db.models import CharField, Value
from django.db.models.functions import Concat
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import decorators, filters, mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from chats.apps.api.v1.internal.projects.serializers import (
    CheckAccessReadSerializer,
    ProjectPermissionReadSerializer,
)
from chats.apps.api.v1.internal.rest_clients.flows_rest_client import FlowRESTClient
from chats.apps.api.v1.permissions import (
    IsProjectAdmin,
    IsSectorManager,
    ProjectAnyPermission,
)
from chats.apps.api.v1.projects.filters import (
    CustomStatusTypeFilterSet,
    FlowStartFilter,
)
from chats.apps.api.v1.projects.serializers import (
    CustomStatusSerializer,
    CustomStatusTypeSerializer,
    LastStatusQueryParamsSerializer,
    LinkContactSerializer,
    ListFlowStartSerializer,
    ListProjectUsersSerializer,
    ProjectFlowContactSerializer,
    ProjectFlowStartSerializer,
    ProjectSerializer,
    SectorDiscussionSerializer,
)
from chats.apps.contacts.models import Contact
from chats.apps.projects.models import (
    ContactGroupFlowReference,
    CustomStatus,
    CustomStatusType,
    Project,
    ProjectPermission,
)
from chats.apps.projects.usecases.integrate_ticketers import IntegratedTicketers
from chats.apps.projects.usecases.status_service import InServiceStatusService
from chats.apps.queues.utils import (
    start_queue_priority_routing_for_all_queues_in_project,
)
from chats.apps.rooms.choices import RoomFeedbackMethods
from chats.apps.rooms.models import Room
from chats.apps.rooms.views import create_room_feedback_message
from chats.apps.sectors.models import Sector

logger = logging.getLogger(__name__)


class ProjectViewset(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    GenericViewSet,
):
    swagger_tag = "Projects"
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [
        IsAuthenticated,
        ProjectAnyPermission,
    ]
    lookup_field = "uuid"

    def get_queryset(self):
        # Allow all projects for internal communication users
        if self.request.user.has_perm("accounts.can_communicate_internally"):
            return super().get_queryset()

        # Allow only projects where the user has access
        return super().get_queryset().filter(permissions__user=self.request.user)

    def list(self, request, *args, **kwargs):
        """List every project the authenticated user can access."""
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """Return the metadata and config for a single project."""
        return super().retrieve(request, *args, **kwargs)

    @action(
        detail=True,
        methods=["GET"],
        url_name="retrieve_linked_contact",
        serializer_class=LinkContactSerializer,
    )
    def retrieve_linked_contact(self, request, *args, **kwargs):
        """Fetch the agent currently linked to the provided contact UUID."""
        project = self.get_object()
        try:
            contactuser = project.linked_contacts.get(contact=request.GET["contact"])
            serializer = LinkContactSerializer(instance=contactuser)
            data = serializer.data
        except (ObjectDoesNotExist, KeyError, AttributeError):
            data = {
                "Detail": "There's no agent linked to the contact or the contact does not exist"
            }

        return Response(data, status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["POST"],
        url_name="create_linked_contact",
        serializer_class=LinkContactSerializer,
    )
    def create_linked_contact(self, request, *args, **kwargs):
        """Link the authenticated agent to the provided contact."""
        project = self.get_object()
        contact = Contact.objects.get(pk=request.data["contact"])

        contactuser, created = project.linked_contacts.get_or_create(
            contact=contact
        )  # Add validation if the instance already exists, return error
        if created:
            contactuser.user = request.user
            contactuser.save()
        serializer = LinkContactSerializer(instance=contactuser)
        if created:
            return Response(serializer.data, status.HTTP_201_CREATED)
        return Response(serializer.data, status.HTTP_200_OK)

    @action(detail=True, methods=["DELETE"], url_name="delete_linked_contact")
    def delete_linked_contact(self, request, *args, **kwargs):
        """Remove the relation between the project and the provided contact UUID."""
        project = self.get_object()
        try:
            contactuser = project.linked_contacts.get(contact=request.GET["contact"])
            contactuser.delete()
        except (ObjectDoesNotExist, KeyError):
            return Response(
                {
                    "Detail": "There's no agent linked to the contact or the contact does not exist"
                },
                status.HTTP_400_BAD_REQUEST,
            )

        return Response({"deleted": True}, status.HTTP_200_OK)

    @action(detail=True, methods=["GET"], url_name="can_trigger_flows")
    def can_trigger_flows(self, request, *args, **kwargs):
        """(Deprecated) Tell whether the user can trigger flows in this project."""
        project = self.get_object()
        can_trigger_flows = project.get_sectors(
            user=request.user, custom_filters={"can_trigger_flows": True}
        ).exists()

        return Response({"can_trigger_flows": can_trigger_flows}, status.HTTP_200_OK)

    @action(detail=True, methods=["GET"], url_name="list_access")
    def list_access(self, request, *args, **kwargs):
        """Return feature flags describing what the requester can do in this project."""
        project = self.get_object()
        context = {}
        context["can_trigger_flows"] = project.get_sectors(
            user=request.user, custom_filters={"can_trigger_flows": True}
        ).exists()

        perm = project.permissions.get(user=self.request.user)
        is_manager = perm.sector_authorizations.exists()
        context["can_access_dashboard"] = perm.is_admin or is_manager

        return Response(context, status.HTTP_200_OK)

    @action(detail=True, methods=["GET"], url_name="contacts")
    def list_contacts(self, request, *args, **kwargs):
        """Return the contact catalog from Weni Flows, respecting cursor pagination."""
        project = self.get_object()
        cursor = request.query_params.get("cursor", "")
        contact_list = FlowRESTClient().list_contacts(
            project, cursor=cursor, query_filters=request.query_params
        )

        return Response(contact_list, status.HTTP_200_OK)

    @action(detail=True, methods=["POST"], url_name="create_contact")
    def create_contacts(self, request, *args, **kwargs):
        """Create a new contact upstream after validating the payload locally."""
        project = self.get_object()
        serializer = ProjectFlowContactSerializer(data=request.data)
        if serializer.is_valid() is False:
            return Response(
                {"Detail": "Data not valid."},
                status.HTTP_400_BAD_REQUEST,
            )
        data = serializer.validated_data
        flows_client = FlowRESTClient()
        urn = data.get("urns")[0]
        if flows_client.validate_contact_exists(urn=urn, project=project):
            return Response(
                "{'urns':['URN belongs to another contact']}",
                status.HTTP_400_BAD_REQUEST,
            )

        contact_response = flows_client.create_contact(project, data)
        contact_response_data = contact_response.json()
        response_status = (
            status.HTTP_201_CREATED
            if contact_response.status_code in [200, 201]
            else status.HTTP_400_BAD_REQUEST
        )
        return Response(contact_response_data, response_status)

    @action(detail=True, methods=["PUT"], url_name="edit_contact")
    def edit_contact(self, request, *args, **kwargs):
        """Update an existing contact in Weni Flows using the provided payload."""
        project = self.get_object()
        serializer = ProjectFlowContactSerializer(data=request.data)
        flows_client = FlowRESTClient()

        if serializer.is_valid() is False:
            return Response(
                {"Detail": "Data not valid."},
                status.HTTP_400_BAD_REQUEST,
            )

        contact_uuid = request.data.get("uuid")
        data = serializer.validated_data

        contact_response = flows_client.create_contact(
            project=project, data=data, contact_id=contact_uuid
        )

        contact_response_data = contact_response.json()
        response_status = (
            status.HTTP_200_OK
            if contact_response.status_code in [200, 201]
            else status.HTTP_400_BAD_REQUEST
        )
        return Response(contact_response_data, response_status)

    @action(detail=True, methods=["GET"], url_name="groups")
    def list_groups(self, request, *args, **kwargs):
        """Return the Flow groups available to the project."""
        project = self.get_object()
        cursor = request.query_params.get("cursor", "")

        contact_list = FlowRESTClient().list_contact_groups(
            project, cursor=cursor, query_filters=request.query_params
        )

        return Response(contact_list, status.HTTP_200_OK)

    @action(detail=True, methods=["GET"], url_name="flows")
    def list_flows(self, request, *args, **kwargs):
        """Return the Flow catalog for this project."""
        project = self.get_object()
        cursor = request.query_params.get("cursor", "")

        flow_list = FlowRESTClient().list_flows(project, cursor=cursor)

        return Response(flow_list, status.HTTP_200_OK)

    @action(detail=True, methods=["GET"], url_name="flows")
    def retrieve_flow_definitions(self, request, *args, **kwargs):
        """Return the raw definition of the selected Flow UUID."""
        project = self.get_object()
        flow_uuid = request.query_params.get("flow", "")

        flow_definitions = FlowRESTClient().retrieve_flow_definitions(
            project, flow_uuid=flow_uuid
        )

        return Response(flow_definitions, status.HTTP_200_OK)

    def _create_flow_start_instances(self, data, flow_start):
        groups = data.get("groups", [])
        contacts = data.get("contacts", [])
        instances = []
        for group in groups:
            reference = ContactGroupFlowReference(
                receiver_type="group", external_id=group, flow_start=flow_start
            )
            instances.append(reference)

        for contact in contacts:
            reference = ContactGroupFlowReference(
                receiver_type="contact", external_id=contact, flow_start=flow_start
            )
            instances.append(reference)

        flow_start.references.bulk_create(instances)

    @action(
        detail=True,
        methods=["POST"],
        url_name="flows",
        serializer_class=ProjectFlowStartSerializer,
    )
    @transaction.atomic  # revert room update if the flows request fails
    def start_flow(self, request, *args, **kwargs):
        """Trigger a Flow for the provided contacts/groups."""
        project = self.get_object()
        serializer = ProjectFlowStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        flow = data.get("flow", None)

        try:
            perm = project.permissions.get(user=request.user)
        except ObjectDoesNotExist:
            return Response(
                {"Detail": "the user does not have permission in this project"},
                status.HTTP_401_UNAUTHORIZED,
            )
        contact_id = data.get("contacts")[0]
        flow_start_data = {
            "permission": perm,
            "flow": flow,
            "contact_data": {
                "name": data.pop("contact_name"),
                "external_id": contact_id,
            },
        }
        room_id = data.get("room", None)

        try:
            room = Room.objects.get(
                pk=room_id, is_active=True, contact__external_id=contact_id
            )
            if room.flowstarts.filter(is_deleted=False).exists():
                return Response(
                    {"Detail": "There already is an active flow start for this room"},
                    status.HTTP_400_BAD_REQUEST,
                )

            if not room.is_24h_valid:
                flow_start_data["room"] = room
                room.request_callback(room.serialized_ws_data)
                room.is_waiting = True
                room.save()
        except (ObjectDoesNotExist, ValidationError):
            pass

        chats_flow_start = project.flowstarts.create(**flow_start_data)
        self._create_flow_start_instances(data, chats_flow_start)

        flow_start = FlowRESTClient().start_flow(project, data)
        chats_flow_start.external_id = flow_start.get("uuid")
        chats_flow_start.name = flow_start.get("flow").get("name")
        chats_flow_start.save()
        feedback = {"name": chats_flow_start.name}
        if chats_flow_start.room:
            create_room_feedback_message(
                room, feedback, method=RoomFeedbackMethods.FLOW_START
            )
            room.notify_room("update")
        return Response(flow_start, status.HTTP_200_OK)

    @action(detail=False, methods=["GET"], url_name="verify-flow-start")
    def retrieve_flow_warning(self, request, *args, **kwargs):
        """Tell whether the contact already has an active room and who is handling it."""
        flows_start_verify = {}
        flows_start_verify["show_warning"] = False

        project_uuid = request.query_params.get("project")
        contact_uuid = request.query_params.get("contact")

        try:
            if not (project := self.get_queryset().filter(uuid=project_uuid).first()):
                return Response(
                    {"project": "Project not found"}, status.HTTP_404_NOT_FOUND
                )
        except Exception as error:
            return Response(
                {"project": f"{type(error)}: {error}"}, status.HTTP_400_BAD_REQUEST
            )

        try:
            if not (
                contact := Contact.objects.filter(external_id=contact_uuid).first()
            ):
                return Response(
                    {"contact": "Contact not found"}, status.HTTP_404_NOT_FOUND
                )
        except Exception as error:
            return Response(
                {"contact": f"{type(error)}: {error}"}, status.HTTP_400_BAD_REQUEST
            )

        try:
            room = Room.objects.get(
                contact=contact, queue__sector__project=project, is_active=True
            )
        except ObjectDoesNotExist:
            return Response(flows_start_verify, status.HTTP_200_OK)

        flows_start_verify["show_warning"] = True
        if room.queue is not None:
            flows_start_verify["queue"] = room.queue.name

        if room.user is not None:
            flows_start_verify["agent"] = room.user.first_name

        return Response(flows_start_verify, status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["GET"],
        url_name="list-flows-start",
    )
    def list_flows_start(self, request, *args, **kwargs):
        """Return the history of Flow starts initiated for this project."""
        project = self.get_object()
        permission = project.permissions.get(user=request.user)
        flow_starts_query = project.flowstarts.exclude(contact_data={}).order_by(
            "-created_on"
        )
        filtro = FlowStartFilter(request.GET, queryset=flow_starts_query)

        queryset = filtro.qs

        if not permission.is_admin:
            queryset = queryset.filter(permission=permission)

        paginator = LimitOffsetPagination()
        flow_starts_queryset_paginated = paginator.paginate_queryset(queryset, request)

        if flow_starts_queryset_paginated is not None:
            serializer = ListFlowStartSerializer(
                flow_starts_queryset_paginated, many=True
            )
            return paginator.get_paginated_response(serializer.data)

        serializer = ListFlowStartSerializer(flow_starts_queryset_paginated, many=True)

        return Response(serializer.data)

    @action(
        detail=True,
        methods=["GET"],
        url_name="list-sectors",
    )
    def list_discussion_sector(self, request, *args, **kwargs):
        """Return the sectors that can host discussions within the project."""
        project = self.get_object()
        queryset = Sector.objects.filter(project=project)

        paginator = LimitOffsetPagination()
        discussion_sectors = paginator.paginate_queryset(queryset, request)

        serializer = SectorDiscussionSerializer(discussion_sectors, many=True)

        return paginator.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=["GET"],
        url_name="list-users",
    )
    def list_users(self, request, *args, **kwargs):
        """Return the agents and managers assigned to this project."""
        project = self.get_object()
        queryset = project.permissions.all()

        paginator = LimitOffsetPagination()
        users = paginator.paginate_queryset(queryset, request)

        serializer = ListProjectUsersSerializer(users, many=True)

        return paginator.get_paginated_response(serializer.data)

    def partial_update(self, request, uuid=None):
        """Partially update project metadata (used to merge config safely)."""
        project = self.get_object()
        config = request.data.get("config")

        if config:
            config = json.loads(config)
            project.config = project.config or {}
            project.config.update(config)
            project.save()
        return Response(ProjectSerializer(project).data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["post"],
        url_path="set-project-principal",
    )
    def set_project_as_principal(self, request, *args, **kwargs):
        """Mark this project as principal and unset the flag for the rest of the org."""
        project = self.get_object()

        config = project.config or {}
        config["its_principal"] = True
        project.config = config
        project.save()

        org_projects = Project.objects.filter(org=project.org).exclude(pk=project.pk)
        org_projects.update(config={"its_principal": False})

        return Response(
            {
                "detail": "Project set as principal and other projects in the same org set as secondary."
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["POST"], url_name="integrate_sectors")
    def integrate_sectors(self, request, *args, **kwargs):
        """Trigger ticketer/topic integration for the provided project UUID."""
        try:
            project_uuid = request.query_params.get("project")

            if not (project := self.get_queryset().filter(uuid=project_uuid).first()):
                return Response(
                    {"project": "Project not found"}, status.HTTP_404_NOT_FOUND
                )

            integrations = IntegratedTicketers()

            integrations.integrate_ticketer(project)
            integrations.integrate_topic(project)
        except Exception as error:
            return Response(
                {"error integrating ticketers": f"{type(error)}: {error}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response("ticketers and topics integrated", status=status.HTTP_200_OK)


class ProjectPermissionViewset(viewsets.ReadOnlyModelViewSet):
    swagger_tag = "Projects"
    queryset = (
        ProjectPermission.objects.all()
        .annotate(
            full_name=Concat(
                "user__first_name",
                Value(" "),
                "user__last_name",
                output_field=CharField(),
            )
        )
        .order_by("full_name")
    )
    serializer_class = ProjectPermissionReadSerializer
    permission_classes = []
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ["user__email", "full_name"]
    filterset_fields = ["project", "role", "status"]
    lookup_field = "uuid"

    def get_permissions(self):
        sector = self.request.query_params.get("sector")

        if sector:
            permission_classes = (IsAuthenticated, IsSectorManager)
        else:
            permission_classes = (IsAuthenticated, IsProjectAdmin)
        return [permission() for permission in permission_classes]

    def list(self, request, *args, **kwargs):
        """List project permissions filtered by project, status, role or sector."""
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """Return the details of a single project permission."""
        return super().retrieve(request, *args, **kwargs)

    @action(detail=False, methods=["GET"], url_name="verify_access")
    def verify_access(self, request, *args, **kwargs):
        """Return the permission data for the current user in the provided project."""
        try:
            instance = ProjectPermission.objects.get(
                user=request.user, project=request.query_params["project"]
            )
            serialized_data = CheckAccessReadSerializer(instance=instance)
        except (KeyError, ProjectPermission.DoesNotExist):
            return Response(
                {"Detail": "You dont have permission in this project."},
                status.HTTP_401_UNAUTHORIZED,
            )
        return Response(serialized_data.data, status.HTTP_200_OK)

    @action(detail=False, methods=["PUT", "PATCH"], url_name="update_access")
    def update_access(self, request, *args, **kwargs):
        """Mark the user's first access as completed for the provided project."""
        try:
            instance = ProjectPermission.objects.get(
                user=request.user, project=request.query_params["project"]
            )
            if instance.first_access is True:
                instance.first_access = False
                instance.save()
            serialized_data = CheckAccessReadSerializer(instance=instance)
        except (KeyError, ProjectPermission.DoesNotExist):
            return Response(
                {"Detail": "You dont have permission in this project."},
                status.HTTP_401_UNAUTHORIZED,
            )
        return Response(serialized_data.data, status=status.HTTP_200_OK)


class CustomStatusTypeViewSet(viewsets.ModelViewSet):
    swagger_tag = "Custom Status"
    queryset = CustomStatusType.objects.all()
    serializer_class = CustomStatusTypeSerializer
    permission_classes = [
        IsAuthenticated,
        ProjectAnyPermission,
    ]
    filter_backends = [DjangoFilterBackend]
    filterset_class = CustomStatusTypeFilterSet

    def get_queryset(self):
        return CustomStatusType.objects.filter(
            is_deleted=False, config__created_by_system__isnull=True
        )

    def perform_create(self, serializer):
        return serializer.save()

    def create(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                data = request.data
                if not isinstance(data, list):
                    data = [data]

                instances = []
                for item in data:
                    serializer = self.get_serializer(data=item)
                    serializer.is_valid(raise_exception=True)
                    instance = self.perform_create(serializer)
                    instances.append(instance)

                response_serializer = self.get_serializer(instances, many=True)
                return Response(
                    response_serializer.data, status=status.HTTP_201_CREATED
                )
        except ValidationError as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        has_active_custom_statuses = CustomStatus.objects.filter(
            status_type=instance, is_active=True
        ).exists()

        if has_active_custom_statuses:
            return Response(
                {
                    "error": (
                        "This status type cannot be deleted because there are "
                        "active CustomStatus records associated with it."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return super().destroy(request, *args, **kwargs)


class CustomStatusViewSet(viewsets.ModelViewSet):
    swagger_tag = "Custom Status"
    queryset = CustomStatus.objects.all()
    serializer_class = CustomStatusSerializer
    permission_classes = [
        IsAuthenticated,
        ProjectAnyPermission,
    ]

    def perform_create(self, serializer):
        user = self.request.user

        status_type = serializer.validated_data.get("status_type")
        project = status_type.project if status_type else None

        with transaction.atomic():
            updated_rows = ProjectPermission.objects.filter(
                user=user, project=project
            ).update(status="OFFLINE")
            if updated_rows == 0:
                raise serializers.ValidationError(
                    {"status": "Can't update user status in project."}
                )

            in_service_type = InServiceStatusService.get_or_create_status_type(project)
            in_service_status = CustomStatus.objects.filter(
                user=user, status_type=in_service_type, is_active=True, project=project
            ).first()

            if in_service_status:
                service_duration = timezone.now() - in_service_status.created_on
                in_service_status.is_active = False
                in_service_status.break_time = int(service_duration.total_seconds())
                in_service_status.save(update_fields=["is_active", "break_time"])

            serializer.save(user=user)

            # Log status change
            from chats.apps.projects.tasks import log_agent_status_change

            log_agent_status_change.delay(
                agent_email=user.email,
                project_uuid=str(project.uuid),
                status="OFFLINE",
                custom_status_name=status_type.name,
                custom_status_type_uuid=str(status_type.uuid),
            )

    @decorators.action(detail=False, methods=["get"])
    def last_status(self, request):
        serializer = LastStatusQueryParamsSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        last_status = (
            CustomStatus.objects.filter(
                user=request.user,
                is_active=True,
                status_type__config__created_by_system__isnull=True,
                status_type__project=serializer.validated_data["project_uuid"],
            )
            .order_by("-created_on")
            .first()
        )

        if last_status:
            return Response(CustomStatusSerializer(last_status).data)

        return Response({"detail": "No status found"}, status=404)

    @action(detail=True, methods=["post"])
    def close_status(self, request, pk=None):
        try:
            instance = CustomStatus.objects.get(pk=pk)

            last_active_status = (
                CustomStatus.objects.filter(
                    user=instance.user,
                    status_type__project=instance.status_type.project,
                    is_active=True,
                )
                .order_by("-created_on")
                .first()
            )

            if last_active_status and last_active_status.uuid != instance.uuid:
                return Response(
                    {
                        "detail": "you can't close this status because it's not the last active status."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            start_queue_priority_routing_for_all_queues_in_project(
                instance.status_type.project
            )

            with transaction.atomic():
                end_time = timezone.now()
                is_active = request.data.get("is_active", False)

                if is_active:
                    updated_rows = ProjectPermission.objects.filter(
                        user=instance.user, project=instance.status_type.project
                    ).update(status="ONLINE")

                    if updated_rows == 0:
                        raise serializers.ValidationError(
                            {"status": "Can't update user status in project."}
                        )

                    # Log status change
                    from chats.apps.projects.tasks import log_agent_status_change

                    log_agent_status_change.delay(
                        agent_email=instance.user.email,
                        project_uuid=str(instance.status_type.project.uuid),
                        status="ONLINE",
                    )

                project_tz = instance.status_type.project.timezone
                local_created_on = instance.created_on.astimezone(project_tz)
                local_end_time = end_time.astimezone(project_tz)

                break_time = int((local_end_time - local_created_on).total_seconds())

                instance.break_time = break_time
                instance.is_active = False
                instance.save()

                room_count = Room.objects.filter(
                    user=instance.user,
                    queue__sector__project=instance.status_type.project,
                    is_active=True,
                ).count()

                has_other_priority = InServiceStatusService.has_priority_status(
                    instance.user, instance.status_type.project
                )

                user_status = ProjectPermission.objects.get(
                    user=instance.user, project=instance.status_type.project
                ).status

                if (
                    room_count > 0
                    and not has_other_priority
                    and user_status == "ONLINE"
                ):
                    in_service_type = InServiceStatusService.get_or_create_status_type(
                        instance.status_type.project
                    )
                    CustomStatus.objects.create(
                        user=instance.user,
                        status_type=in_service_type,
                        is_active=True,
                        project=instance.status_type.project,
                        break_time=0,
                        created_on=end_time,
                    )

                return Response(
                    {"detail": "CustomStatus updated successfully."},
                    status=status.HTTP_200_OK,
                )

        except CustomStatus.DoesNotExist:
            return Response(
                {"detail": "Custom Status not found."}, status=status.HTTP_404_NOT_FOUND
            )
