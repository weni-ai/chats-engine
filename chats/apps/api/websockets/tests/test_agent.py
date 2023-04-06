from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.test import RequestFactory, TestCase

from chats.apps.accounts.authentication.channels.middleware import TokenAuthMiddleware
from chats.apps.api.utils import create_user_and_token
from chats.apps.api.websockets.rooms.routing import websocket_urlpatterns
from chats.apps.contacts.models import Contact
from chats.apps.projects.models import Project
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector, SectorAuthorization


class AgentConsumerTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.application = TokenAuthMiddleware(URLRouter(websocket_urlpatterns))

        self.user, self.token = create_user_and_token(nickname="agent")
        self.project = Project.objects.create(name="Test chat Project 1")
        self.user_permission = self.project.permissions.create(user=self.user, role=1)
        self.sector = Sector.objects.create(
            name="Test chat Sector 1",
            project=self.project,
            rooms_limit=3,
            work_start="07:00",
            work_end="17:00",
        )
        self.sector_permission = SectorAuthorization.objects.create(
            sector=self.sector, permission=self.user_permission, role=1
        )
        self.queue = self.sector.queues.create(name="Test chat queue 1")
        self.contact = Contact.objects.create(
            name="Contact test 123", email="test@user.com"
        )
        self.room = Room.objects.create(
            queue=self.queue, contact=self.contact, is_active=True
        )

    async def test_authenticate_ok(self):
        agent_comunicator = WebsocketCommunicator(
            self.application,
            f"/ws/agent/rooms?Token={self.token.pk}&project={self.project.pk}",
        )
        connected, subprotocol = await agent_comunicator.connect()
        self.assertTrue(connected)
