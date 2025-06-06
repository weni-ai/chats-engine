from datetime import time
from unittest import mock

from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory, force_authenticate

from chats.apps.accounts.models import User
from chats.apps.api.v1.msgs.permissions import MessageMediaPermission, MessagePermission
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


class TestMessagePermission(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.permission = MessagePermission()
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
        )
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            work_start=time(9, 0),  # 9:00 AM
            work_end=time(18, 0),  # 6:00 PM
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.room = Room.objects.create(queue=self.queue, user=self.user)
        self.project_permission = ProjectPermission.objects.create(
            user=self.user, project=self.project, role=1
        )

    def test_has_permission_list_success(self):
        """
        Tests listing permission when user has access
        """
        request = self.factory.get(f"/api/v1/msgs/?room={self.room.uuid}")
        force_authenticate(request, user=self.user)
        request = Request(request)
        view = mock.Mock(action="list")

        result = self.permission.has_permission(request, view)
        self.assertTrue(result)

    def test_has_permission_list_project_success(self):
        """
        Tests listing permission by project when user has access
        """
        request = self.factory.get(f"/api/v1/msgs/?project={self.project.uuid}")
        force_authenticate(request, user=self.user)
        request = Request(request)
        view = mock.Mock(action="list")

        result = self.permission.has_permission(request, view)
        self.assertTrue(result)

    def test_has_permission_list_no_access(self):
        """
        Tests listing permission when user has no access
        """
        other_user = User.objects.create_user(
            email="other@example.com",
            password="testpass123",
            first_name="Other",
            last_name="User",
        )

        ProjectPermission.objects.create(user=other_user, project=self.project, role=0)

        request = self.factory.get(f"/api/v1/msgs/?room={self.room.uuid}")
        force_authenticate(request, user=other_user)
        request = Request(request)
        view = mock.Mock(action="list")

        result = self.permission.has_permission(request, view)
        self.assertFalse(result)

    def test_has_object_permission_success(self):
        """
        Tests object permission when user is room owner
        """
        request = self.factory.get("/api/v1/msgs/1/")
        force_authenticate(request, user=self.user)
        request = Request(request)
        message = mock.Mock(room=self.room)

        result = self.permission.has_object_permission(request, None, message)
        self.assertTrue(result)

    def test_has_object_permission_anonymous(self):
        """
        Tests object permission with anonymous user
        """
        request = self.factory.get("/api/v1/msgs/1/")
        request = Request(request)
        request.user = AnonymousUser()
        message = mock.Mock(room=self.room)

        result = self.permission.has_object_permission(request, None, message)
        self.assertFalse(result)


class TestMessageMediaPermission(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.permission = MessageMediaPermission()
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
        )
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            work_start=time(9, 0),
            work_end=time(18, 0),
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.room = Room.objects.create(queue=self.queue, user=self.user)
        self.project_permission = ProjectPermission.objects.create(
            user=self.user, project=self.project, role=1
        )

    def test_has_permission_list_room_success(self):
        """
        Tests listing permission by room when user has access
        """
        request = self.factory.get(f"/api/v1/msgs/media/?room={self.room.uuid}")
        force_authenticate(request, user=self.user)
        request = Request(request)
        view = mock.Mock(action="list")

        result = self.permission.has_permission(request, view)
        self.assertTrue(result)

    def test_has_permission_list_project_success(self):
        """
        Tests listing permission by project when user has access
        """
        request = self.factory.get(f"/api/v1/msgs/media/?project={self.project.uuid}")
        force_authenticate(request, user=self.user)
        request = Request(request)
        view = mock.Mock(action="list")

        result = self.permission.has_permission(request, view)
        self.assertTrue(result)

    def test_has_permission_list_no_access(self):
        """
        Tests listing permission when user has no access
        """
        other_user = User.objects.create_user(
            email="other@example.com",
            password="testpass123",
            first_name="Other",
            last_name="User",
        )

        ProjectPermission.objects.create(user=other_user, project=self.project, role=0)

        request = self.factory.get(f"/api/v1/msgs/media/?room={self.room.uuid}")
        force_authenticate(request, user=other_user)
        request = Request(request)
        view = mock.Mock(action="list")

        result = self.permission.has_permission(request, view)
        self.assertFalse(result)

    def test_has_object_permission_success(self):
        """
        Tests object permission when user is room owner
        """
        request = self.factory.get("/api/v1/msgs/media/1/")
        force_authenticate(request, user=self.user)
        request = Request(request)
        obj = mock.Mock(message=mock.Mock(room=self.room))

        result = self.permission.has_object_permission(request, None, obj)
        self.assertTrue(result)

    def test_has_object_permission_anonymous(self):
        """
        Tests object permission with anonymous user
        """
        request = self.factory.get("/api/v1/msgs/media/1/")
        request = Request(request)
        request.user = AnonymousUser()
        obj = mock.Mock(message=mock.Mock(room=self.room))

        result = self.permission.has_object_permission(request, None, obj)
        self.assertFalse(result)
