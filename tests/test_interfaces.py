from django.test import SimpleTestCase

from chats.apps.api.v1.dashboard.interfaces import CacheRepository, RoomsDataRepository


class DummyRoomsRepo(RoomsDataRepository):
    def get_cache_key(self, filters):
        return "key"

    def get_rooms_data(self, filters):
        return []


class InterfaceTests(SimpleTestCase):
    def test_rooms_data_repository_is_abstract(self):
        with self.assertRaises(TypeError):
            RoomsDataRepository()

    def test_cache_repository_is_abstract(self):
        with self.assertRaises(TypeError):
            CacheRepository()

    def test_rooms_data_repository_concrete(self):
        repo = DummyRoomsRepo()
        self.assertEqual(repo.get_cache_key(None), "key")
        self.assertEqual(repo.get_rooms_data(None), [])
