from django.test import TestCase

from chats.apps.accounts.models import User
from chats.apps.projects.models.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.utils import create_transfer_json, get_data_from_object
from chats.apps.sectors.models import Sector


class TestUtils(TestCase):
    def setUp(self):
        self.user_a = User.objects.create(
            first_name="John", last_name="Doe", email="john.doe@example.com"
        )
        self.user_b = User.objects.create(
            first_name="Jane", last_name="Doe", email="jane.doe@example.com"
        )
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=20,
            work_start="11:20",
            work_end="23:20",
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)

    def test_get_data_from_object_user(self):
        assert get_data_from_object(self.user_a) == {
            "type": "user",
            "name": self.user_a.name,
            "email": self.user_a.email,
            "id": str(self.user_a.id),
        }

    def test_get_data_from_object_queue(self):
        assert get_data_from_object(self.queue) == {
            "type": "queue",
            "name": self.queue.name,
            "uuid": str(self.queue.uuid),
        }

    def test_create_transfer_json_from_user_to_queue(self):
        assert create_transfer_json("forward", self.user_a, self.queue) == {
            "action": "forward",
            "from": {
                "type": "user",
                "name": self.user_a.name,
                "email": self.user_a.email,
                "id": str(self.user_a.id),
            },
            "to": {
                "type": "queue",
                "name": "Test Queue",
                "uuid": str(self.queue.uuid),
            },
        }

    def test_create_transfer_json_from_none_to_queue(self):
        assert create_transfer_json("forward", None, self.queue) == {
            "action": "forward",
            "from": {"type": "", "name": ""},
            "to": {
                "type": "queue",
                "name": self.queue.name,
                "uuid": str(self.queue.uuid),
            },
        }

    def test_create_transfer_json_from_user_to_user(self):
        assert create_transfer_json("forward", self.user_a, self.user_b) == {
            "action": "forward",
            "from": {
                "type": "user",
                "name": self.user_a.name,
                "email": self.user_a.email,
                "id": str(self.user_a.id),
            },
            "to": {
                "type": "user",
                "name": self.user_b.name,
                "email": self.user_b.email,
                "id": str(self.user_b.id),
            },
        }
