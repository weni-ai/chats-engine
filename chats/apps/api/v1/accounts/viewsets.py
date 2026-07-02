from django.utils import timezone
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from rest_framework import mixins, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from chats.apps.accounts.models import User
from chats.apps.api.v1.accounts.serializers import (
    LoginSerializer,
    UserDataQueryParamsSerializer,
    UserNameSerializer,
)


@method_decorator(
    name="create", decorator=swagger_auto_schema(responses={201: '{"token":"TOKEN"}'})
)
class LoginViewset(mixins.CreateModelMixin, viewsets.GenericViewSet):

    swagger_tag = "Authentication"

    """
    Login Users
    """

    queryset = User.objects
    serializer_class = LoginSerializer
    lookup_field = ("username", "password")

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )

        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])

        token, created = Token.objects.get_or_create(user=user)
        return Response(
            {"token": token.key},
            status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class UserDataViewset(viewsets.GenericViewSet):

    swagger_tag = "Users"
    queryset = User.objects.only("email", "first_name", "last_name").all()
    serializer_class = UserNameSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = None

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        if user.has_perm("accounts.can_communicate_internally"):
            return qs

        shared_project_ids = user.project_permissions.values("project")
        return qs.filter(project_permissions__project__in=shared_project_ids).distinct()

    def retrieve(self, request, *args, **kwargs):
        params = UserDataQueryParamsSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        user_email = params.validated_data["user_email"]

        user = self.get_queryset().filter(email=user_email).first()
        if user is None:
            return Response({"detail": "Email not found"}, status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(user)
        return Response(serializer.data)
