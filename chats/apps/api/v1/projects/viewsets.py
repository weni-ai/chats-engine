from django.core.exceptions import ObjectDoesNotExist
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ObjectDoesNotExist
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


from chats.apps.api.v1.projects.serializers import (
    ProjectSerializer,
    ProjectFlowStartSerializer,
    ProjectFlowContactSerializer,
    LinkContactSerializer,
)
from chats.apps.api.v1.internal.projects.serializers import (
    ProjectPermissionReadSerializer,
    CheckAccessReadSerializer,
)
from chats.apps.projects.models import (
    Project,
    ProjectPermission,
    ContactGroupFlowReference,
)

from chats.apps.contacts.models import Contact

from chats.apps.api.v1.permissions import (
    IsProjectAdmin,
    IsSectorManager,
    ProjectAnyPermission,
)

from chats.apps.api.v1.internal.rest_clients.flows_rest_client import FlowRESTClient


class ProjectViewset(viewsets.ReadOnlyModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [
        IsAuthenticated,
        ProjectAnyPermission,
    ]
    lookup_field = "uuid"

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                "contact",
                openapi.IN_QUERY,
                description="Contact's UUID",
                type=openapi.TYPE_STRING,
                format="uuid",
            )
        ]
    )
    @action(
        detail=True,
        methods=["GET"],
        url_name="retrieve_linked_contact",
        serializer_class=LinkContactSerializer,
    )
    def retrieve_linked_contact(self, request, *args, **kwargs):
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

    @swagger_auto_schema(
        methods=["post"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["contact"],
            properties={
                "contact": openapi.Schema(type=openapi.TYPE_STRING, format="uuid")
            },
        ),
        operation_description="contact's uuid",
    )
    @action(
        detail=True,
        methods=["POST"],
        url_name="create_linked_contact",
        serializer_class=LinkContactSerializer,
    )
    def create_linked_contact(self, request, *args, **kwargs):
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

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                "contact",
                openapi.IN_QUERY,
                description="Contact's UUID",
                type=openapi.TYPE_STRING,
                format="uuid",
            )
        ]
    )
    @action(detail=True, methods=["DELETE"], url_name="delete_linked_contact")
    def delete_linked_contact(self, request, *args, **kwargs):
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
        project = self.get_object()
        can_trigger_flows = project.get_sectors(
            user=request.user, custom_filters={"can_trigger_flows": True}
        ).exists()

        return Response({"can_trigger_flows": can_trigger_flows}, status.HTTP_200_OK)

    @action(detail=True, methods=["GET"], url_name="contacts")
    def list_contacts(self, request, *args, **kwargs):
        project = self.get_object()
        cursor = request.query_params.get("cursor", "")
        contact_list = FlowRESTClient().list_contacts(project, cursor=cursor)

        return Response(contact_list, status.HTTP_200_OK)

    @action(detail=True, methods=["POST"], url_name="create_contact")
    def create_contacts(self, request, *args, **kwargs):
        project = self.get_object()
        serializer = ProjectFlowContactSerializer(data=request.data)
        if serializer.is_valid() is False:
            return Response(
                {"Detail": "Data not valid."},
                status.HTTP_400_BAD_REQUEST,
            )
        data = serializer.validated_data
        contact = FlowRESTClient().create_contact(project, data)

        return Response(contact, status.HTTP_201_CREATED)

    @action(detail=True, methods=["GET"], url_name="groups")
    def list_groups(self, request, *args, **kwargs):
        project = self.get_object()
        cursor = request.query_params.get("cursor", "")

        contact_list = FlowRESTClient().list_contact_groups(project, cursor=cursor)

        return Response(contact_list, status.HTTP_200_OK)

    @action(detail=True, methods=["GET"], url_name="flows")
    def list_flows(self, request, *args, **kwargs):
        project = self.get_object()
        cursor = request.query_params.get("cursor", "")

        flow_list = FlowRESTClient().list_flows(project, cursor=cursor)

        return Response(flow_list, status.HTTP_200_OK)

    @action(detail=True, methods=["GET"], url_name="flows")
    def retrieve_flow_definitions(self, request, *args, **kwargs):
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

    @action(detail=True, methods=["POST"], url_name="flows")
    def start_flow(self, request, *args, **kwargs):
        project = self.get_object()
        serializer = ProjectFlowStartSerializer(data=request.data)
        if serializer.is_valid() is False:
            return Response(
                {"Detail": "Invalid data."},
                status.HTTP_400_BAD_REQUEST,
            )
        data = serializer.validated_data
        flow = data.get("flow", None)

        try:
            perm = project.permissions.get(user=request.user)
        except ObjectDoesNotExist:
            return Response(
                {"Detail": "the user does not have permission in this project"},
                status.HTTP_401_UNAUTHORIZED,
            )
        chats_flow_start = project.flowstarts.create(permission=perm, flow=flow)

        self._create_flow_start_instances(data, chats_flow_start)

        flow_start = FlowRESTClient().start_flow(project, data)
        chats_flow_start.external_id = flow_start.get("uuid")
        chats_flow_start.save()
        return Response(flow_start, status.HTTP_200_OK)


class ProjectPermissionViewset(viewsets.ReadOnlyModelViewSet):
    queryset = ProjectPermission.objects.all()
    serializer_class = ProjectPermissionReadSerializer
    permission_classes = []
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["project", "role", "status"]
    lookup_field = "uuid"

    def get_permissions(self):
        sector = self.request.query_params.get("sector")

        if sector:
            permission_classes = (IsAuthenticated, IsSectorManager)
        else:
            permission_classes = (IsAuthenticated, IsProjectAdmin)
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=["GET"], url_name="verify_access")
    def verify_access(self, request, *args, **kwargs):
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
