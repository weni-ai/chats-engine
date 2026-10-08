import uuid

from django.test import TestCase

from chats.apps.projects.models import Project
from chats.apps.projects.usecases.resolve_project_for_unified_sac_migration import (
    MissingProjectUUIDError,
    ProjectMismatchError,
    ProjectNotFoundError,
    ResolveProjectForUnifiedSacMigrationUseCase,
)


class ResolveProjectForUnifiedSacMigrationUseCaseTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Principal", org="org-resolve")
        self.use_case = ResolveProjectForUnifiedSacMigrationUseCase()

    def test_raises_when_project_uuid_is_missing(self):
        with self.assertRaises(MissingProjectUUIDError):
            self.use_case.execute(None)
        with self.assertRaises(MissingProjectUUIDError):
            self.use_case.execute("")

    def test_returns_jwt_project_when_uuids_match(self):
        project = self.use_case.execute(
            str(self.project.uuid), jwt_project=self.project
        )
        self.assertEqual(project, self.project)

    def test_raises_when_jwt_project_does_not_match(self):
        other = Project.objects.create(name="Other", org="org-resolve-other")
        with self.assertRaises(ProjectMismatchError):
            self.use_case.execute(str(other.uuid), jwt_project=self.project)

    def test_returns_project_from_database(self):
        project = self.use_case.execute(str(self.project.uuid))
        self.assertEqual(project.pk, self.project.pk)

    def test_raises_when_project_does_not_exist(self):
        with self.assertRaises(ProjectNotFoundError):
            self.use_case.execute(str(uuid.uuid4()))

    def test_raises_when_project_uuid_is_invalid(self):
        with self.assertRaises(ProjectNotFoundError):
            self.use_case.execute("not-a-uuid")
