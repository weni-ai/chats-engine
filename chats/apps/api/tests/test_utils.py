from datetime import timedelta
from unittest.mock import Mock

import pytz
from django.test import TestCase
from django.utils import timezone

from chats.apps.accounts.models import User
from chats.apps.api.utils import (
    calculate_in_service_time,
    create_contact,
    create_message,
    create_reply_index,
    create_room_dto,
    create_user_and_token,
    ensure_timezone,
    verify_user_room,
)
from chats.apps.ai_features.history_summary.models import HistorySummaryStatus
from chats.apps.api.v1.dashboard.serializers import DashboardRoomSerializer
from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import ChatMessageReplyIndex, Message
from chats.apps.projects.models.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


class TestApiUtils(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="P")
        self.sector = Sector.objects.create(
            name="S",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Q", sector=self.sector)
        self.room = Room.objects.create(queue=self.queue)

    def test_create_user_and_token(self):
        user, token = create_user_and_token("nick")
        self.assertIsInstance(user, User)
        self.assertEqual(user.email, "nick@user.com")
        self.assertEqual(token.user, user)

    def test_create_message_returns_none_when_user_equals_contact(self):
        same_obj = Mock()
        res = create_message("x", room=self.room, user=same_obj, contact=same_obj)
        self.assertIsNone(res)

    def test_create_message_persists_when_ok(self):
        user = User.objects.create(email="u@e.com")
        contact = Contact.objects.create(name="C")
        m = create_message("hello", room=self.room, user=user, contact=contact)
        self.assertIsInstance(m, Message)
        self.assertEqual(m.text, "hello")

    def test_create_contact_sets_external_id(self):
        c = create_contact("Name", "n@e.com")
        self.assertTrue(c.external_id)

    def test_create_room_dto(self):
        data = create_room_dto({"interact_time": 10, "response_time": 5, "waiting_time": 2})
        self.assertIsInstance(data, list)
        self.assertEqual(set(data[0].keys()), set(DashboardRoomSerializer().fields.keys()))

    def test_verify_user_room(self):
        req_email = "req@e.com"
        req_user = User.objects.create(email=req_email)
        # when room.user is set
        agent = User.objects.create(email="a@e.com")
        self.room.user = agent
        self.room.save()
        self.assertEqual(verify_user_room(self.room, req_email), agent)
        # when room.user is not set, returns user_request
        self.room.user = None
        self.room.save()
        self.assertEqual(verify_user_room(self.room, req_email), req_user)

    def test_ensure_timezone_naive_and_aware(self):
        tz = pytz.timezone("UTC")
        naive = timezone.now().replace(tzinfo=None)
        aware = ensure_timezone(naive, tz)
        self.assertIsNotNone(aware.tzinfo)
        already_aware = timezone.now()
        self.assertEqual(ensure_timezone(already_aware, tz), already_aware)

    def test_create_reply_index(self):
        m_no = Message.objects.create(room=self.room, text="n")
        create_reply_index(m_no)
        self.assertFalse(ChatMessageReplyIndex.objects.exists())
        m_yes = Message.objects.create(room=self.room, text="y", external_id="ext-1")
        create_reply_index(m_yes)
        self.assertTrue(ChatMessageReplyIndex.objects.filter(external_id="ext-1", message=m_yes).exists())

    def test_calculate_in_service_time_active_online(self):
        created_on = (timezone.now() - timedelta(seconds=3)).isoformat()
        lst = [{"status_type": "In-Service", "is_active": True, "created_on": created_on}]
        total = calculate_in_service_time(lst, user_status="ONLINE")
        self.assertGreaterEqual(total, 2)

    def test_calculate_in_service_time_break_time(self):
        lst = [{"status_type": "In-Service", "is_active": False, "break_time": 7}]
        total = calculate_in_service_time(lst, user_status="OFFLINE")
        self.assertEqual(total, 7)
