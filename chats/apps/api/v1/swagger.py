from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="Weni Chats API",
        default_version="v1",
        description="-",
        terms_of_service="https://weni.ai/termos-de-uso/",
        contact=openapi.Contact(email="helder.souza@weni.ai"),
        license=openapi.License(name="GPL-3.0"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)
