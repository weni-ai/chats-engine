from django.utils.translation import gettext_lazy as _
from rest_framework import status, mixins
from rest_framework.response import Response

from django.utils import timezone
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from rest_framework.authtoken.models import Token
from rest_framework.viewsets import GenericViewSet

from chats.apps.accounts.models import User
from chats.apps.api.v1.accounts.serializers import LoginSerializer


@method_decorator(
    name="create", decorator=swagger_auto_schema(responses={201: '{"token":"TOKEN"}'})
)
class LoginViewset(mixins.CreateModelMixin, GenericViewSet):

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
