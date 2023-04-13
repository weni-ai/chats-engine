# import uuid

# from django.urls import reverse
# from rest_framework.authtoken.models import Token
# from rest_framework.test import APITestCase
# from rest_framework import status

# from chats.apps.accounts.models import User
# from chats.apps.projects.models import Project


# class FlowStartTests(APITestCase):
#     fixtures = ["chats/fixtures/fixture_app.json"]

#     def _create_flow_start(self, auth_token, project, data):
#         client = self.client
#         client.credentials(HTTP_AUTHORIZATION=auth_token)
#         url = reverse("project-flows", kwargs={"uuid": str(project.pk)})
#         return client.post(url, data=data, format="json")

#     def test_without_data(self):
#         project = Project.objects.get(pk="34a93b52-231e-11ed-861d-0242ac120002")
#         user_admin = User.objects.get(email="amazoninhaweni@chats.weni.ai")
#         token = Token.objects.get_or_create(user=user_admin)[0]
#         flow_start_data = {}
#         response = self._create_flow_start(
#             auth_token=f"Token {token.pk}", data=flow_start_data, project=project
#         )

#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

#     def test_create_flow_start_for_one_nonexistent_contact_no_groups(self):
#         project = Project.objects.get(pk="34a93b52-231e-11ed-861d-0242ac120002")
#         user_admin = User.objects.get(email="amazoninhaweni@chats.weni.ai")
#         token = Token.objects.get_or_create(user=user_admin)[0]
#         flow_id = str(uuid.uuid4())
#         contact_id = str(uuid.uuid4())

#         flow_start_data = {
#             "groups": [],
#             "contacts": [
#                 contact_id,
#             ],
#             "flow": flow_id,
#         }
#         response = self._create_flow_start(
#             auth_token=f"Token {token.pk}", data=flow_start_data, project=project
#         )
#         flow_start = project.flowstarts.get(flow=flow_id)
#         flow_start_reference = (
#             flow_start.references.get()
#         )  # should have only one reference, thus no need to filter

#         self.assertIsNone(flow_start.room)
#         self.assertEqual(flow_start_reference.receiver_type, "contact")
#         self.assertEqual(flow_start_reference.external_id, contact_id)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
