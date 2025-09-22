from django.utils import timezone
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from rest_framework import mixins, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from chats.apps.accounts.models import User
from chats.apps.api.v1.accounts.serializers import LoginSerializer, UserNameSerializer
from chats.core.cache_utils import get_user_id_by_email_cached


@method_decorator(
    name="create", decorator=swagger_auto_schema(responses={201: '{"token":"TOKEN"}'})
)
class LoginViewset(mixins.CreateModelMixin, viewsets.GenericViewSet):
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
    queryset = User.objects.only("email", "first_name", "last_name").all()
    serializer_class = UserNameSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = None

    def get_object(self):
        user_email = self.request.query_params.get("user_email")
        uid = get_user_id_by_email_cached(user_email)
        if uid is None:
            raise User.DoesNotExist()
        return User.objects.only("email", "first_name", "last_name").get(pk=uid)

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except User.DoesNotExist:
            return Response({"detail": "Email not found"}, status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
