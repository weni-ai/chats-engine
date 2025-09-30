from django.test import TestCase

from chats.apps.api.authentication.token import JWTTokenGenerator


class JWTTokenGeneratorTests(TestCase):
    def test_generate_token(self):
        token_generator = JWTTokenGenerator()
        token = token_generator.generate_token(payload={"test": "test"})
        self.assertIsNotNone(token)

    def test_verify_token(self):
        token_generator = JWTTokenGenerator()
        token = token_generator.generate_token(payload={"test": "test"})
        self.assertIsNotNone(token)
        verified_token = token_generator.verify_token(token)
        self.assertIsNotNone(verified_token)
        self.assertEqual(verified_token["test"], "test")
