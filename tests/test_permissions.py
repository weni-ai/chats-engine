from types import SimpleNamespace
from django.test import SimpleTestCase

from chats.apps.api.v1.contacts.permissions import ContactRelatedRetrievePermission


class DummyObj:
    def __init__(self, can_retrieve_return):
        self._ret = can_retrieve_return

    def can_retrieve(self, user, project):
        # Usando validações diretas, em vez de assert
        if project != "proj-1" or user != "user":
            raise ValueError("Argumentos incorretos para can_retrieve")
        return self._ret


class ContactPermissionsTests(SimpleTestCase):
    def _make_request(self, user, project=None):
        """Return a minimal request object with attributes used by the permission class."""
        return SimpleNamespace(user=user, query_params={"project": project})
    
    def test_has_object_permission_granted(self):
        # Arrange
        perm = ContactRelatedRetrievePermission()
        obj = DummyObj(True)
        request = self._make_request("user", project="proj-1")
        
        # Act & Assert
        self.assertTrue(perm.has_object_permission(request, view=None, obj=obj))
    
    def test_has_object_permission_denied(self):
        # Arrange
        perm = ContactRelatedRetrievePermission()
        obj = DummyObj(False)
        request = self._make_request("user", project="proj-1")
        
        # Act & Assert
        self.assertFalse(perm.has_object_permission(request, view=None, obj=obj)) 