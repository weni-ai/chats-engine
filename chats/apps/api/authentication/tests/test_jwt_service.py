import uuid

from django.test import TestCase
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from chats.apps.api.authentication.services.jwt_service import JWTService


def generate_private_key():
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )


def generate_private_key_pem(private_key: rsa.RSAPrivateKey):
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")


def generate_public_key(private_key):
    return private_key.public_key()


def generate_public_key_pem(public_key: rsa.RSAPublicKey):
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")


class JWTServiceTests(TestCase):
    def test_generate_jwt_token(self):
        jwt_service = JWTService()
        token = jwt_service.generate_jwt_token(
            project_uuid=uuid.uuid4(),
            key=generate_private_key_pem(generate_private_key()),
        )
        self.assertIsNotNone(token)
