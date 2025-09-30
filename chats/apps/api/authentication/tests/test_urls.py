from django.urls import path
from chats.apps.api.authentication.tests.test_classes import MockView

urlpatterns = [
    path("mock/", MockView.as_view(), name="mock_view"),
]
