from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.api.utils import create_contact, create_user_and_token
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector, SectorAuthorization
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.contacts.models import Contact


class BaseAPIChatsTestCase(APITestCase):
    base_url = None

    def setUp(self):
        # USERS
        self.admin, self.admin_token = create_user_and_token("admin")
        self.admin_2, self.admin_2_token = create_user_and_token("admin 2")

        self.manager, self.manager_token = create_user_and_token("manager")
        self.manager_2, self.manager_2_token = create_user_and_token("manager")
        self.manager_3, self.manager_3_token = create_user_and_token("manager 3")

        self.agent, self.agent_token = create_user_and_token("agent")
        self.agent_2, self.agent_2_token = create_user_and_token("agent2")

        # CONTACTS
        self.contact = create_contact("Contact", "contatc@mail.com")
        self.contact_2 = create_contact("Contact2", "contatc2@mail.com")
        self.contact_3 = create_contact("Contact3", "contatc3@mail.com")
        self.contact_4 = create_contact("Contact4", "contatc4@mail.com")

        # PROJECTS
        self.project = Project.objects.create(
            name="Test Project", connect_pk="asdasdas-dad-as-sda-d-ddd"
        )
        self.project_2 = Project.objects.create(
            name="Test Project", connect_pk="asdasdas-dad-as-sda-d-ddd"
        )

        # PROJECT AUTHORIZATIONS
        self.admin_auth = self.project.authorizations.create(
            user=self.admin, role=ProjectPermission.ROLE_ADMIN
        )

        self.admin_2_auth = self.project.authorizations.create(
            user=self.admin_2, role=ProjectPermission.ROLE_ADMIN
        )
        # SECTORS
        self.sector_1 = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
        )
        self.sector_2 = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=5,
            work_start="07:00",
            work_end="17:00",
        )
        self.sector_3 = Sector.objects.create(
            name="Sector on project 2",
            project=self.project_2,
            rooms_limit=1,
            work_start="07:00",
            work_end="17:00",
        )

        # SECTOR AUTHORIZATIONS
        self.manager_auth = self.sector_1.set_user_authorization(
            self.manager, role=SectorAuthorization.ROLE_MANAGER
        )
        self.manager_2_auth = self.sector_2.set_user_authorization(
            self.manager_2, role=SectorAuthorization.ROLE_MANAGER
        )
        self.manager_2_auth_1 = self.sector_3.set_user_authorization(
            self.manager, role=SectorAuthorization.ROLE_MANAGER
        )

        # QUEUES
        self.queue_1 = Queue.objects.create(name="Q1", sector=self.sector_1)
        self.queue_2 = Queue.objects.create(name="Q2", sector=self.sector_1)
        self.queue_3 = Queue.objects.create(name="Q3", sector=self.sector_2)

        self.queue_4 = Queue.objects.create(name="Q4", sector=self.sector_3)

        # QUEUE AUTHORIZATIONS
        self.agent_1_auth = self.queue_1.authorization.create(
            user=self.agent, role=QueueAuthorization.ROLE_AGENT
        )
        self.agent_2_auth = self.queue_2.authorization.create(
            user=self.agent_2, role=QueueAuthorization.ROLE_AGENT
        )
        self.agent_2_auth_2 = self.queue_3.authorization.create(
            user=self.agent_2, role=QueueAuthorization.ROLE_AGENT
        )

        # ROOMS
        self.room_1 = Room.objects.create(
            contact=self.contact, queue=self.queue_1, user=self.agent
        )
        self.room_2 = Room.objects.create(contact=self.contact_2, queue=self.queue_2)

        self.room_3 = Room.objects.create(contact=self.contact_3, queue=self.queue_3)

        self.room_4 = Room.objects.create(contact=self.contact_4, queue=self.queue_4)

        self.count_project_1_contact = 3
        self.count_manager_contact = 2
        self.count_agent_contact = 1

    def create_contact(
        self, name: str = "João da Silva", email="joao.da.silva@email.com"
    ):
        c = Contact.objects.create(name=name, email=email)
        return c
