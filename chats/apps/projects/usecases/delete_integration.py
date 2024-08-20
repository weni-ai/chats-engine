from django.contrib.auth import get_user_model

from chats.apps.projects.models.models import Project, ProjectPermission
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.sectors.models import Sector, SectorAuthorization, SectorTag
from chats.apps.feature_version.models import FeatureVersion

from chats.apps.api.v1.dto.sector_dto import SectorDTO, dto_to_dict
from chats.apps.api.v1.dto.queue_dto import QueueDTO

from chats.apps.api.v1.internal.eda_clients.flows_eda_client import FlowsEDAClient
from chats.apps.projects.usecases.exceptions import InvalidFeatureVersion

User = get_user_model()


class DeleteIntegrationUseCase:
    def delete(self, feature_version_dto):
        try:
            feature_version = FeatureVersion.objects.get(
                project=feature_version_dto.project,
                feature_version=feature_version_dto.feature_version,
            )
        except Exception:
            raise InvalidFeatureVersion(f"Feature version does not exists!")

        sectors_data = feature_version.sectors

        for sector in sectors_data:
            sector_uuid = sector["uuid"]
            manager_emails = sector["manager_email"]

            sector_instance = Sector.objects.get(uuid=sector_uuid)

            if sector_instance:
                SectorAuthorization.objects.filter(
                    sector=sector_instance,
                    permission__user__email__in=manager_emails,
                    role=SectorAuthorization.ROLE_MANAGER,
                ).delete()

                for queue in sector.get("queues", []):
                    queue_uuid = queue["uuid"]
                    agents_emails = queue["agents"]

                    queue_instance = Queue.objects.get(uuid=queue_uuid)

                    if queue_instance:
                        QueueAuthorization.objects.filter(
                            queue=queue_instance,
                            permission__user__email__in=agents_emails,
                        ).delete()

                        queue_instance.delete()
                sector_instance.delete()

        feature_version.delete()
