from django.test import TestCase
from django.db import models

from chats.core.managers import SoftDeletableManager
from chats.core.models import BaseSoftDeleteModel


class TestOnlyModel(BaseSoftDeleteModel):
    """
    A test-only model that won't exist outside these tests.
    This model is used to test the SoftDeletableManager functionality.
    """

    name = models.CharField(max_length=100)

    class Meta:
        app_label = "core"
        db_table = "test_only_soft_deletable_model"


class SoftDeletableManagerTests(TestCase):
    def setUp(self):
        self.instance = TestOnlyModel.objects.create(name="Example")

    def test_get_queryset_with_include_deleted(self):
        self.assertIn(self.instance, TestOnlyModel.objects.all())
        self.assertIn(self.instance, TestOnlyModel.all_objects.all())

        self.instance.delete()

        self.assertNotIn(self.instance, TestOnlyModel.objects.all())
        self.assertIn(self.instance, TestOnlyModel.all_objects.all())
