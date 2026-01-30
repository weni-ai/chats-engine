from django.test import TestCase

from chats.apps.core.internal_domains import (
    get_vtex_internal_domains_with_at_symbol,
    is_vtex_internal_domain,
    exclude_vtex_internal_domains,
)
from chats.apps.accounts.models import User


class InternalDomainsTestCase(TestCase):
    def test_is_vtex_internal_domain(self):
        domains = get_vtex_internal_domains_with_at_symbol()

        for domain in domains:
            self.assertTrue(is_vtex_internal_domain("test" + domain))

        self.assertFalse(is_vtex_internal_domain("test@gmail.com"))
        self.assertFalse(is_vtex_internal_domain(""))
        self.assertFalse(is_vtex_internal_domain(None))

        for domain in domains:
            altered_domain = "test" + domain.replace("@", "@another")

            self.assertFalse(is_vtex_internal_domain(altered_domain))

    def test_exclude_vtex_internal_domains(self):
        domains = get_vtex_internal_domains_with_at_symbol()

        for domain in domains:
            User.objects.create(email="test" + domain)
            User.objects.create(email="test" + domain.replace("@", "@another"))

        non_internal_user = User.objects.create(email="test@gmail.com")

        users = User.objects.all()

        filtered_users = exclude_vtex_internal_domains(users)

        self.assertEqual(
            filtered_users.count(), len(domains) + 1
        )  # modified domains + non internal user
        self.assertIn(non_internal_user, filtered_users)

        for domain in domains:
            self.assertNotIn(User.objects.get(email="test" + domain), filtered_users)
            self.assertIn(
                User.objects.get(email="test" + domain.replace("@", "@another")),
                filtered_users,
            )
