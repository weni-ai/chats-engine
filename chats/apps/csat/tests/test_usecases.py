from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings

from chats.apps.accounts.models import User
from chats.apps.csat.usecases.notify_admins_about_not_found_csat_flow import (
    NotifyAdminsAboutNotFoundCSATFlow,
)
from chats.apps.projects.models.models import Project, ProjectPermission


class TestNotifyAdminsAboutNotFoundCSATFlow(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.admin_user = User.objects.create_user(
            email="admin@example.com",
            password="testpass",
            language="en-us",
        )
        ProjectPermission.objects.create(
            project=self.project,
            user=self.admin_user,
            role=ProjectPermission.ROLE_ADMIN,
        )

    @override_settings(SEND_EMAILS=False)
    def test_does_not_send_email_when_send_emails_is_disabled(self):
        usecase = NotifyAdminsAboutNotFoundCSATFlow(self.project)
        usecase.execute()

        self.assertEqual(len(mail.outbox), 0)

    @override_settings(SEND_EMAILS=True, DEFAULT_FROM_EMAIL="noreply@test.com")
    def test_does_not_send_email_when_project_has_no_admins(self):
        project_without_admins = Project.objects.create(name="Empty Project")

        usecase = NotifyAdminsAboutNotFoundCSATFlow(project_without_admins)
        usecase.execute()

        self.assertEqual(len(mail.outbox), 0)

    @override_settings(SEND_EMAILS=True, DEFAULT_FROM_EMAIL="noreply@test.com")
    def test_sends_email_to_all_admin_emails(self):
        second_admin = User.objects.create_user(
            email="admin2@example.com",
            password="testpass",
            language="en-us",
        )
        ProjectPermission.objects.create(
            project=self.project,
            user=second_admin,
            role=ProjectPermission.ROLE_ADMIN,
        )

        usecase = NotifyAdminsAboutNotFoundCSATFlow(self.project)
        usecase.execute()

        self.assertEqual(len(mail.outbox), 1)

        sent_email = mail.outbox[0]
        self.assertIn("admin@example.com", sent_email.to)
        self.assertIn("admin2@example.com", sent_email.to)
        self.assertEqual(sent_email.from_email, "noreply@test.com")

    @override_settings(SEND_EMAILS=True, DEFAULT_FROM_EMAIL="noreply@test.com")
    def test_email_subject_contains_project_name(self):
        usecase = NotifyAdminsAboutNotFoundCSATFlow(self.project)
        usecase.execute()

        sent_email = mail.outbox[0]
        self.assertIn(self.project.name, sent_email.subject)

    @override_settings(SEND_EMAILS=True, DEFAULT_FROM_EMAIL="noreply@test.com")
    def test_email_body_contains_project_name(self):
        usecase = NotifyAdminsAboutNotFoundCSATFlow(self.project)
        usecase.execute()

        sent_email = mail.outbox[0]
        self.assertIn(self.project.name, sent_email.body)

    @override_settings(SEND_EMAILS=True, DEFAULT_FROM_EMAIL="noreply@test.com")
    def test_email_includes_html_alternative(self):
        usecase = NotifyAdminsAboutNotFoundCSATFlow(self.project)
        usecase.execute()

        sent_email = mail.outbox[0]
        self.assertEqual(len(sent_email.alternatives), 1)

        html_content, mime_type = sent_email.alternatives[0]
        self.assertEqual(mime_type, "text/html")
        self.assertIn(self.project.name, html_content)

    @override_settings(
        SEND_EMAILS=True,
        DEFAULT_FROM_EMAIL="noreply@test.com",
        DEFAULT_LANGUAGE="en-us",
    )
    def test_uses_default_language_when_admins_have_no_language(self):
        self.admin_user.language = ""
        self.admin_user.save(update_fields=["language"])

        usecase = NotifyAdminsAboutNotFoundCSATFlow(self.project)
        usecase.execute()

        self.assertEqual(len(mail.outbox), 1)

    @override_settings(SEND_EMAILS=True, DEFAULT_FROM_EMAIL="noreply@test.com")
    def test_excludes_soft_deleted_admin_permissions(self):
        ProjectPermission.objects.filter(
            project=self.project,
            user=self.admin_user,
        ).update(is_deleted=True)

        usecase = NotifyAdminsAboutNotFoundCSATFlow(self.project)
        usecase.execute()

        self.assertEqual(len(mail.outbox), 0)

    @override_settings(SEND_EMAILS=True, DEFAULT_FROM_EMAIL="noreply@test.com")
    @patch(
        "chats.apps.csat.usecases.notify_admins_about_not_found_csat_flow.EmailMultiAlternatives"
    )
    def test_logs_error_when_email_send_fails(self, mock_email_cls):
        mock_email_cls.return_value.send.side_effect = Exception("SMTP error")

        usecase = NotifyAdminsAboutNotFoundCSATFlow(self.project)

        with self.assertLogs(
            "chats.apps.csat.usecases.notify_admins_about_not_found_csat_flow",
            level="ERROR",
        ) as logs:
            usecase.execute()

        self.assertTrue(
            any(
                "Failed to send custom flow not found email" in msg
                for msg in logs.output
            )
        )

    @override_settings(SEND_EMAILS=True, DEFAULT_FROM_EMAIL="noreply@test.com")
    def test_does_not_raise_when_email_send_fails(self):
        with patch(
            "chats.apps.csat.usecases.notify_admins_about_not_found_csat_flow.EmailMultiAlternatives"
        ) as mock_email_cls:
            mock_email_cls.return_value.send.side_effect = Exception("SMTP error")

            usecase = NotifyAdminsAboutNotFoundCSATFlow(self.project)
            usecase.execute()
