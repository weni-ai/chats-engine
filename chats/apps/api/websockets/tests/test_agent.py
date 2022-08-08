from channels.testing import WebsocketCommunicator
from django.test import RequestFactory, TestCase

from chats.apps.api.utils import create_message, create_user_and_token
from chats.apps.api.websockets.rooms.consumers.agent import AgentRoomConsumer
from chats.apps.contacts.models import Contact
from chats.apps.projects.models import Project
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector, SectorAuthorization


class AgentConsumerTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

        self.user, self.Token = create_user_and_token(nickname="agent")
        self.project = Project.objects.create(name="Test chat Project 1")
        self.sector = Sector.objects.create(
            name="Test chat Sector 1",
            project=self.project,
            rooms_limit=3,
            work_start=7,
            work_end=17,
        )
        self.sector_permission = SectorAuthorization.objects.create(
            sector=self.sector, user=self.user, role=1
        )
        self.contact = Contact.objects.create(
            name="Contact test 123", email="test@user.com"
        )
        self.room = Room.objects.create(
            sector=self.sector, contact=self.contact, is_active=True
        )

    async def test_authenticate_ok(self):
        agent_comunicator = WebsocketCommunicator(
            AgentRoomConsumer.as_asgi(), f"/ws/agent/rooms?Token={self.Token.pk}"
        )
        connected, subprotocol = await agent_comunicator.connect()
        self.assertTrue(connected)
