import uuid

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.contacts.models import Contact
from chats.apps.projects.models.models import Project, ProjectPermission
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector, SectorAuthorization


class RoomsCountByQueueViewBase(APITestCase):
    def setUp(self):
        self.url = reverse("rooms-count-by-queue")

        self.project = Project.objects.create(name="Test Project")

        self.sector_a = Sector.objects.create(
            name="A Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.sector_b = Sector.objects.create(
            name="B Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )

        self.queue_a1 = Queue.objects.create(name="A1 Queue", sector=self.sector_a)
        self.queue_a2 = Queue.objects.create(name="A2 Queue", sector=self.sector_a)
        self.queue_b1 = Queue.objects.create(name="B1 Queue", sector=self.sector_b)

        self.agent = User.objects.create_user(email="agent@test.com")

    def _create_room(self, queue, *, user=None, is_active=True, is_waiting=False):
        return Room.objects.create(
            queue=queue,
            contact=Contact.objects.create(),
            user=user,
            is_active=is_active,
            is_waiting=is_waiting,
        )

    def _authenticate(self, user):
        self.client.force_authenticate(user=user)

    def _get(self, params=None):
        return self.client.get(self.url, params or {})

    def _flatten(self, payload):
        result = {}
        for sector in payload["sectors"]:
            for queue in sector["queues"]:
                result[queue["uuid"]] = {
                    "sector": sector["name"],
                    "queued": queue["rooms_in_awaiting"],
                    "in_service": queue["rooms_in_progress"],
                }
        return result


class RoomsCountByQueueViewAdminTests(RoomsCountByQueueViewBase):
    def setUp(self):
        super().setUp()

        self.admin = User.objects.create_user(email="admin@test.com")
        ProjectPermission.objects.create(
            user=self.admin,
            project=self.project,
            role=ProjectPermission.ROLE_ADMIN,
        )
        self._authenticate(self.admin)

    def test_unauthenticated_returns_401(self):
        self.client.force_authenticate(user=None)
        response = self._get({"project": str(self.project.uuid)})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_project_returns_403(self):
        response = self._get({})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_without_permission_returns_403(self):
        outsider = User.objects.create_user(email="outsider@test.com")
        self._authenticate(outsider)
        response = self._get({"project": str(self.project.uuid)})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unknown_project_returns_403(self):
        response = self._get({"project": str(uuid.uuid4())})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_empty_project_returns_no_sectors(self):
        empty_project = Project.objects.create(name="Empty Project")
        ProjectPermission.objects.create(
            user=self.admin,
            project=empty_project,
            role=ProjectPermission.ROLE_ADMIN,
        )

        response = self._get({"project": str(empty_project.uuid)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"sectors": []})

    def test_admin_sees_all_sectors_and_queues_with_zero_counts(self):
        response = self._get({"project": str(self.project.uuid)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        sectors = response.data["sectors"]
        self.assertEqual([s["name"] for s in sectors], ["A Sector", "B Sector"])

        flat = self._flatten(response.data)
        self.assertEqual(
            set(flat.keys()),
            {
                str(self.queue_a1.uuid),
                str(self.queue_a2.uuid),
                str(self.queue_b1.uuid),
            },
        )
        for queue_data in flat.values():
            self.assertEqual(queue_data["queued"], 0)
            self.assertEqual(queue_data["in_service"], 0)

    def test_admin_counts_queued_and_in_service(self):
        self._create_room(self.queue_a1)
        self._create_room(self.queue_a1)
        self._create_room(self.queue_a1, user=self.agent)
        self._create_room(self.queue_b1, user=self.agent)

        response = self._get({"project": str(self.project.uuid)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        flat = self._flatten(response.data)

        self.assertEqual(flat[str(self.queue_a1.uuid)]["queued"], 2)
        self.assertEqual(flat[str(self.queue_a1.uuid)]["in_service"], 1)
        self.assertEqual(flat[str(self.queue_a2.uuid)]["queued"], 0)
        self.assertEqual(flat[str(self.queue_a2.uuid)]["in_service"], 0)
        self.assertEqual(flat[str(self.queue_b1.uuid)]["queued"], 0)
        self.assertEqual(flat[str(self.queue_b1.uuid)]["in_service"], 1)

    def test_counts_ignore_inactive_and_flow_start_rooms(self):
        self._create_room(self.queue_a1)
        self._create_room(self.queue_a1, is_active=False)
        self._create_room(self.queue_a1, is_waiting=True)
        self._create_room(self.queue_a1, user=self.agent)
        self._create_room(self.queue_a1, user=self.agent, is_active=False)
        self._create_room(self.queue_a1, user=self.agent, is_waiting=True)

        response = self._get({"project": str(self.project.uuid)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        flat = self._flatten(response.data)
        self.assertEqual(flat[str(self.queue_a1.uuid)]["queued"], 1)
        self.assertEqual(flat[str(self.queue_a1.uuid)]["in_service"], 1)

    def test_soft_deleted_sector_is_hidden(self):
        self._create_room(self.queue_b1)
        self.sector_b.is_deleted = True
        self.sector_b.save(update_fields=["is_deleted"])

        response = self._get({"project": str(self.project.uuid)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        sector_names = [s["name"] for s in response.data["sectors"]]
        self.assertNotIn("B Sector", sector_names)

    def test_sectors_and_queues_are_alphabetically_ordered(self):
        Queue.objects.create(name="A0 Queue", sector=self.sector_a)

        response = self._get({"project": str(self.project.uuid)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        sectors = response.data["sectors"]
        self.assertEqual([s["name"] for s in sectors], ["A Sector", "B Sector"])

        sector_a_queues = [q["name"] for q in sectors[0]["queues"]]
        self.assertEqual(sector_a_queues, ["A0 Queue", "A1 Queue", "A2 Queue"])

    def test_does_not_count_rooms_from_other_projects(self):
        other_project = Project.objects.create(name="Other")
        other_sector = Sector.objects.create(
            name="Other Sector",
            project=other_project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        other_queue = Queue.objects.create(name="Other Queue", sector=other_sector)
        self._create_room(other_queue)

        response = self._get({"project": str(self.project.uuid)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        sector_names = [s["name"] for s in response.data["sectors"]]
        self.assertNotIn("Other Sector", sector_names)


class RoomsCountByQueueViewAttendantAccessTests(RoomsCountByQueueViewBase):
    """
    Attendants with a ProjectPermission on the project can call the
    endpoint. Visibility is restricted to their authorized queues and
    `rooms_in_progress` only counts rooms assigned to themselves.
    """

    def test_attendant_with_queue_authorization_only_sees_authorized_queues(self):
        attendant = User.objects.create_user(email="attendant@test.com")
        attendant_permission = ProjectPermission.objects.create(
            user=attendant,
            project=self.project,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        QueueAuthorization.objects.create(
            permission=attendant_permission,
            queue=self.queue_a1,
            role=QueueAuthorization.ROLE_AGENT,
        )
        self._authenticate(attendant)

        self._create_room(self.queue_a1)
        self._create_room(self.queue_a1, user=attendant)
        self._create_room(self.queue_a1, user=self.agent)
        self._create_room(self.queue_b1, user=self.agent)

        response = self._get({"project": str(self.project.uuid)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        flat = self._flatten(response.data)
        self.assertEqual(set(flat.keys()), {str(self.queue_a1.uuid)})
        self.assertEqual(flat[str(self.queue_a1.uuid)]["queued"], 1)
        self.assertEqual(flat[str(self.queue_a1.uuid)]["in_service"], 1)

    def test_attendant_without_any_queue_authorization_returns_empty(self):
        attendant = User.objects.create_user(email="attendant@test.com")
        ProjectPermission.objects.create(
            user=attendant,
            project=self.project,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        self._authenticate(attendant)

        response = self._get({"project": str(self.project.uuid)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"sectors": []})


class RoomsCountByQueueViewSectorManagerTests(RoomsCountByQueueViewBase):
    def setUp(self):
        super().setUp()

        self.manager = User.objects.create_user(email="manager@test.com")
        self.manager_permission = ProjectPermission.objects.create(
            user=self.manager,
            project=self.project,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        SectorAuthorization.objects.create(
            permission=self.manager_permission,
            sector=self.sector_a,
            role=SectorAuthorization.ROLE_MANAGER,
        )
        self._authenticate(self.manager)

    def test_sector_manager_sees_in_service_counts(self):
        self._create_room(self.queue_a1)
        self._create_room(self.queue_a1, user=self.agent)

        response = self._get({"project": str(self.project.uuid)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        flat = self._flatten(response.data)
        self.assertEqual(flat[str(self.queue_a1.uuid)]["queued"], 1)
        self.assertEqual(flat[str(self.queue_a1.uuid)]["in_service"], 1)


class RoomsCountByQueueViewTargetEmailTests(RoomsCountByQueueViewBase):
    """
    View-mode: when an `email` query param is provided, the counts and
    visibility must reflect what that target user would see, not the
    requester.
    """

    def setUp(self):
        super().setUp()

        self.requester_admin = User.objects.create_user(email="requester@test.com")
        ProjectPermission.objects.create(
            user=self.requester_admin,
            project=self.project,
            role=ProjectPermission.ROLE_ADMIN,
        )

        self.target_attendant = User.objects.create_user(email="target@test.com")
        target_perm = ProjectPermission.objects.create(
            user=self.target_attendant,
            project=self.project,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        QueueAuthorization.objects.create(
            permission=target_perm,
            queue=self.queue_a1,
            role=QueueAuthorization.ROLE_AGENT,
        )

        self._authenticate(self.requester_admin)

    def test_email_param_restricts_queues_to_target_attendant(self):
        self._create_room(self.queue_a1)
        self._create_room(self.queue_a2)
        self._create_room(self.queue_b1)

        response = self._get(
            {
                "project": str(self.project.uuid),
                "email": self.target_attendant.email,
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        flat = self._flatten(response.data)
        self.assertEqual(set(flat.keys()), {str(self.queue_a1.uuid)})

    def test_email_param_in_service_only_counts_target_user_rooms(self):
        self._create_room(self.queue_a1, user=self.target_attendant)
        self._create_room(self.queue_a1, user=self.agent)

        response = self._get(
            {
                "project": str(self.project.uuid),
                "email": self.target_attendant.email,
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        flat = self._flatten(response.data)
        self.assertEqual(flat[str(self.queue_a1.uuid)]["in_service"], 1)

    def test_email_param_with_admin_target_filters_in_service_by_email(self):
        admin_target = User.objects.create_user(email="admin_target@test.com")
        ProjectPermission.objects.create(
            user=admin_target,
            project=self.project,
            role=ProjectPermission.ROLE_ADMIN,
        )

        self._create_room(self.queue_a1, user=admin_target)
        self._create_room(self.queue_a1, user=self.agent)
        self._create_room(self.queue_b1, user=self.agent)

        response = self._get(
            {
                "project": str(self.project.uuid),
                "email": admin_target.email,
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        flat = self._flatten(response.data)
        self.assertEqual(
            set(flat.keys()),
            {
                str(self.queue_a1.uuid),
                str(self.queue_a2.uuid),
                str(self.queue_b1.uuid),
            },
        )
        self.assertEqual(flat[str(self.queue_a1.uuid)]["in_service"], 1)
        self.assertEqual(flat[str(self.queue_b1.uuid)]["in_service"], 0)
        total_in_service = sum(q["in_service"] for q in flat.values())
        self.assertEqual(total_in_service, 1)

    def test_email_param_with_admin_target_zero_in_service_when_no_rooms(self):
        admin_target = User.objects.create_user(email="admin_target@test.com")
        ProjectPermission.objects.create(
            user=admin_target,
            project=self.project,
            role=ProjectPermission.ROLE_ADMIN,
        )

        self._create_room(self.queue_a1, user=self.agent)
        self._create_room(self.queue_b1, user=self.agent)

        response = self._get(
            {
                "project": str(self.project.uuid),
                "email": admin_target.email,
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        flat = self._flatten(response.data)
        total_in_service = sum(q["in_service"] for q in flat.values())
        self.assertEqual(total_in_service, 0)

    def test_no_email_uses_request_user(self):
        self._create_room(self.queue_a1, user=self.requester_admin)
        self._create_room(self.queue_b1, user=self.agent)

        response = self._get({"project": str(self.project.uuid)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        flat = self._flatten(response.data)
        total_in_service = sum(q["in_service"] for q in flat.values())
        self.assertEqual(total_in_service, 2)

    def test_email_invalid_format_returns_400(self):
        response = self._get(
            {
                "project": str(self.project.uuid),
                "email": "not-an-email",
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_email_param_for_user_without_project_permission_returns_404(self):
        outsider = User.objects.create_user(email="outsider@test.com")

        response = self._get(
            {
                "project": str(self.project.uuid),
                "email": outsider.email,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_email_param_for_unknown_user_returns_404(self):
        response = self._get(
            {
                "project": str(self.project.uuid),
                "email": "ghost@test.com",
            }
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_empty_email_param_falls_back_to_request_user(self):
        self._create_room(self.queue_a1, user=self.requester_admin)
        self._create_room(self.queue_b1, user=self.agent)

        response = self._get(
            {
                "project": str(self.project.uuid),
                "email": "",
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        flat = self._flatten(response.data)
        total_in_service = sum(q["in_service"] for q in flat.values())
        self.assertEqual(total_in_service, 2)
