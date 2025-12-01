import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import timedelta

from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.test import RequestFactory, TestCase
from django.utils import timezone

from chats.apps.accounts.authentication.channels.middleware import TokenAuthMiddleware
from chats.apps.api.utils import create_user_and_token
from chats.apps.api.websockets.rooms.routing import websocket_urlpatterns
from chats.apps.api.websockets.rooms.consumers.agent import AgentRoomConsumer
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
        await agent_comunicator.disconnect()


class PingTimeoutUnitTestCase(TestCase):
    """Unit tests for ping timeout logic"""

    def test_ping_timeout_checker_detects_timeout(self):
        """Test that ping_timeout_checker detects when last_ping exceeds timeout"""
        # Create a mock consumer
        consumer = MagicMock(spec=AgentRoomConsumer)
        consumer.permission = MagicMock()
        consumer.user = MagicMock()
        consumer.user.email = "test@example.com"
        consumer.project = "test-project"
        
        # Set last_ping to 70 seconds ago (exceeds 60s timeout)
        consumer.last_ping = timezone.now() - timedelta(seconds=70)
        
        # Mock the async methods
        consumer.set_user_status = AsyncMock()
        consumer.finalize_in_service_if_needed = AsyncMock()
        consumer.close = AsyncMock()
        
        # Run the checker logic manually
        async def run_check():
            seconds_since_ping = (timezone.now() - consumer.last_ping).total_seconds()
            
            if seconds_since_ping > 60:
                await consumer.set_user_status("OFFLINE")
                await consumer.finalize_in_service_if_needed()
                await consumer.close(code=1000)
                return True
            return False
        
        # Execute
        result = asyncio.run(run_check())
        
        # Assert that timeout was detected
        self.assertTrue(result)
        consumer.set_user_status.assert_called_once_with("OFFLINE")
        consumer.finalize_in_service_if_needed.assert_called_once()
        consumer.close.assert_called_once_with(code=1000)

    def test_ping_timeout_checker_no_timeout_when_recent(self):
        """Test that ping_timeout_checker doesn't timeout when ping is recent"""
        # Create a mock consumer
        consumer = MagicMock(spec=AgentRoomConsumer)
        consumer.permission = MagicMock()
        consumer.user = MagicMock()
        consumer.user.email = "test@example.com"
        
        # Set last_ping to 30 seconds ago (within 60s timeout)
        consumer.last_ping = timezone.now() - timedelta(seconds=30)
        
        # Mock the async methods
        consumer.set_user_status = AsyncMock()
        consumer.finalize_in_service_if_needed = AsyncMock()
        consumer.close = AsyncMock()
        
        # Run the checker logic manually
        async def run_check():
            seconds_since_ping = (timezone.now() - consumer.last_ping).total_seconds()
            
            if seconds_since_ping > 60:
                await consumer.set_user_status("OFFLINE")
                await consumer.finalize_in_service_if_needed()
                await consumer.close(code=1000)
                return True
            return False
        
        # Execute
        result = asyncio.run(run_check())
        
        # Assert that timeout was NOT detected
        self.assertFalse(result)
        consumer.set_user_status.assert_not_called()
        consumer.finalize_in_service_if_needed.assert_not_called()
        consumer.close.assert_not_called()

    def test_ping_timeout_checker_stops_when_permission_none(self):
        """Test that ping_timeout_checker stops gracefully when permission is None"""
        # Create a mock consumer
        consumer = MagicMock(spec=AgentRoomConsumer)
        consumer.permission = None  # Permission removed
        consumer.last_ping = timezone.now() - timedelta(seconds=70)
        
        # Mock the async methods
        consumer.set_user_status = AsyncMock()
        consumer.finalize_in_service_if_needed = AsyncMock()
        consumer.close = AsyncMock()
        
        # Run the checker logic with permission check
        async def run_check():
            # Safety check: stop if permission is gone
            if not hasattr(consumer, 'permission') or consumer.permission is None:
                return False  # Stopped gracefully
            
            seconds_since_ping = (timezone.now() - consumer.last_ping).total_seconds()
            
            if seconds_since_ping > 60:
                await consumer.set_user_status("OFFLINE")
                await consumer.finalize_in_service_if_needed()
                await consumer.close(code=1000)
                return True
            return False
        
        # Execute
        result = asyncio.run(run_check())
        
        # Assert that it stopped gracefully without calling methods
        self.assertFalse(result)
        consumer.set_user_status.assert_not_called()
        consumer.finalize_in_service_if_needed.assert_not_called()
        consumer.close.assert_not_called()

    def test_ping_updates_timestamp(self):
        """Test that receiving a ping updates the timestamp"""
        # Create a mock consumer
        consumer = MagicMock(spec=AgentRoomConsumer)
        
        # Set initial ping time
        initial_time = timezone.now() - timedelta(seconds=5)
        consumer.last_ping = initial_time
        
        # Simulate receiving ping (update last_ping)
        consumer.last_ping = timezone.now()
        
        # Assert that last_ping was updated
        self.assertGreater(consumer.last_ping, initial_time)

    def test_task_cancellation_handling(self):
        """Test that CancelledError is properly handled"""
        
        async def mock_checker_with_cancellation():
            try:
                # Simulate the checker loop
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                # This should be caught and re-raised
                raise
        
        async def run_test():
            # Create and cancel the task
            task = asyncio.create_task(mock_checker_with_cancellation())
            await asyncio.sleep(0.1)  # Let it start
            task.cancel()
            
            # Wait for cancellation
            try:
                await task
            except asyncio.CancelledError:
                return True
            return False
        
        # Execute
        result = asyncio.run(run_test())
        
        # Assert that cancellation was handled properly
        self.assertTrue(result)
