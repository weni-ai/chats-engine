from django.db.models import Q
from django.test import TestCase

from chats.apps.accounts.models import User
from chats.apps.contacts.models import Contact
from chats.apps.projects.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.channel_filters import (
    CHANNEL_URN_PREFIXES,
    KNOWN_URN_PREFIXES,
    apply_channels_filter,
    channels_q,
    normalize_channels,
)
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector

CHANNEL_URN_SAMPLES = {
    "instagram": "instagram:user123",
    "facebook": "facebook:page456",
    "whatsapp": "whatsapp:5511999999999",
    "teams": "teams:thread-id",
    "msteams": "msteams:thread-id",
    "email": "email:ada@example.com",
    "mailto": "mailto:ada@example.com",
    "ext": "ext:shopping-id",
    "shopping_assistant": "shopping_assistant:cart-id",
    "telegram": "telegram:999",
    "empty": "",
}


class NormalizeChannelsTests(TestCase):
    def test_none_and_empty(self):
        self.assertIsNone(normalize_channels(None))
        self.assertIsNone(normalize_channels(""))
        self.assertIsNone(normalize_channels([]))

    def test_comma_separated_and_repeated_list(self):
        self.assertEqual(
            normalize_channels("whatsapp,instagram"),
            ["whatsapp", "instagram"],
        )
        self.assertEqual(
            normalize_channels(["whatsapp", "email,teams"]),
            ["whatsapp", "email", "teams"],
        )


class ChannelsQMappingTests(TestCase):
    def test_each_known_channel_uses_expected_prefixes(self):
        expected = {
            "instagram": ("instagram:",),
            "facebook": ("facebook:",),
            "whatsapp": ("whatsapp:",),
            "teams": ("teams:", "msteams:"),
            "email": ("email:", "mailto:"),
            "shopping_assistant": ("ext:", "shopping_assistant:"),
        }
        self.assertEqual(CHANNEL_URN_PREFIXES, expected)

    def test_others_negates_all_known_prefixes(self):
        q = channels_q(["others"])
        known = Q()
        for prefix in KNOWN_URN_PREFIXES:
            known |= Q(urn__startswith=prefix)
        self.assertEqual(str(q), str(~known))

    def test_invalid_channel_is_ignored(self):
        self.assertIsNone(channels_q(["not_a_channel"]))

    def test_union_of_two_channels(self):
        q = channels_q(["whatsapp", "instagram"])
        expected = Q(urn__startswith="whatsapp:") | Q(urn__startswith="instagram:")
        self.assertEqual(str(q), str(expected))


class ApplyChannelsFilterTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Channel Filter Project")
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=10,
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)
        self.user = User.objects.create_user(email="agent@test.com")
        self.rooms = {}
        for key, urn in CHANNEL_URN_SAMPLES.items():
            self.rooms[key] = Room.objects.create(
                queue=self.queue,
                contact=Contact.objects.create(name=f"Contact {key}"),
                user=self.user,
                urn=urn,
            )

    def _uuids(self, channels):
        return set(
            apply_channels_filter(Room.objects.all(), channels).values_list(
                "uuid", flat=True
            )
        )

    def test_whatsapp_matches_only_whatsapp_prefix(self):
        self.assertEqual(self._uuids(["whatsapp"]), {self.rooms["whatsapp"].uuid})

    def test_instagram_matches_only_instagram_prefix(self):
        self.assertEqual(self._uuids(["instagram"]), {self.rooms["instagram"].uuid})

    def test_facebook_matches_only_facebook_prefix(self):
        self.assertEqual(self._uuids(["facebook"]), {self.rooms["facebook"].uuid})

    def test_teams_matches_teams_and_msteams(self):
        self.assertEqual(
            self._uuids(["teams"]),
            {self.rooms["teams"].uuid, self.rooms["msteams"].uuid},
        )

    def test_email_matches_email_and_mailto(self):
        self.assertEqual(
            self._uuids(["email"]),
            {self.rooms["email"].uuid, self.rooms["mailto"].uuid},
        )

    def test_shopping_assistant_matches_ext_and_shopping_assistant(self):
        self.assertEqual(
            self._uuids(["shopping_assistant"]),
            {self.rooms["ext"].uuid, self.rooms["shopping_assistant"].uuid},
        )

    def test_others_excludes_all_known_prefixes(self):
        self.assertEqual(
            self._uuids(["others"]),
            {self.rooms["telegram"].uuid, self.rooms["empty"].uuid},
        )

    def test_others_does_not_include_ext_or_msteams(self):
        others = self._uuids(["others"])
        self.assertNotIn(self.rooms["ext"].uuid, others)
        self.assertNotIn(self.rooms["msteams"].uuid, others)

    def test_multiple_channels_are_union(self):
        self.assertEqual(
            self._uuids(["whatsapp", "instagram"]),
            {self.rooms["whatsapp"].uuid, self.rooms["instagram"].uuid},
        )
