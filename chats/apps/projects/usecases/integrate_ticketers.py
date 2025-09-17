import logging

from rest_framework import exceptions, status

from chats.apps.api.v1.internal.rest_clients.flows_rest_client import FlowRESTClient
from chats.apps.projects.models import Project
from chats.apps.queues.models import Queue
from chats.apps.sectors.models import Sector

logger = logging.getLogger(__name__)


class IntegratedTicketers:
    def __init__(self):
        self.flows_client = FlowRESTClient()

    def _check_ticketer_exists(self, sector_uuid: str) -> bool:
        """Check if a ticketer has already been marked as integrated."""
        try:
            sector = Sector.objects.get(uuid=sector_uuid)
            config = sector.config or {}
            return config.get("ticketer_integrated", False)
        except Sector.DoesNotExist:
            return False

    def _check_queue_exists(self, queue_uuid: str) -> bool:
        """Check if a queue has already been marked as integrated."""
        try:
            queue = Queue.objects.get(uuid=queue_uuid)
            config = queue.config or {}
            return config.get("queue_integrated", False)
        except Queue.DoesNotExist:
            return False

    def _mark_ticketer_integrated(self, sector_uuid: str):
        """Mark a sector as having an integrated ticketer."""
        try:
            sector = Sector.objects.get(uuid=sector_uuid)
            config = sector.config or {}
            config["ticketer_integrated"] = True
            sector.config = config
            sector.save(update_fields=["config"])
        except Exception as e:
            logger.error(f"Error marking ticketer as integrated: {e}")

    def _mark_queue_integrated(self, queue_uuid: str):
        """Mark a queue as having been integrated."""
        try:
            queue = Queue.objects.get(uuid=queue_uuid)
            config = queue.config or {}
            config["queue_integrated"] = True
            queue.config = config
            queue.save(update_fields=["config"])
        except Exception as e:
            logger.error(f"Error marking queue as integrated: {e}")

    def integrate_ticketer(self, project):
        """Integrate all ticketers from a principal project with secondary projects."""
        projects = Project.objects.filter(org=project.org, config__its_principal=False)
        integrated_count = 0
        skipped_count = 0

        for secondary_project in projects:
            sectors = Sector.objects.filter(
                project=project,
                config__secondary_project=str(secondary_project.uuid),
            )

            for sector in sectors:
                # Check if already integrated
                if self._check_ticketer_exists(str(sector.uuid)):
                    logger.info(
                        f"Ticketer for sector {sector.uuid} already integrated, skipping"
                    )
                    skipped_count += 1
                    continue

                content = {
                    "project_uuid": str(secondary_project.uuid),
                    "name": sector.name,
                    "config": {
                        "project_auth": str(sector.external_token.pk),
                        "sector_uuid": str(sector.uuid),
                    },
                }

                try:
                    response = self.flows_client.create_ticketer(**content)

                    if response.status_code in [
                        status.HTTP_200_OK,
                        status.HTTP_201_CREATED,
                    ]:
                        self._mark_ticketer_integrated(str(sector.uuid))
                        integrated_count += 1
                        logger.info(
                            f"Successfully integrated ticketer for sector {sector.uuid}"
                        )
                    else:
                        raise exceptions.APIException(
                            detail=(
                                f"[{response.status_code}] Error posting the sector/ticketer "
                                f"on flows. Exception: {response.content}"
                            )
                        )

                except Exception as e:
                    logger.error(
                        f"Error integrating ticketer for sector {sector.uuid}: {e}"
                    )
                    raise

        logger.info(
            f"Integration completed: {integrated_count} integrated, {skipped_count} skipped"
        )
        return {"integrated": integrated_count, "skipped": skipped_count}

    def integrate_topic(self, project):
        """Integrate all queues from a principal project with secondary projects."""
        projects = Project.objects.filter(org=project.org, config__its_principal=False)
        integrated_count = 0
        skipped_count = 0

        for secondary_project in projects:
            queues = Queue.objects.filter(
                sector__project=project,
                sector__config__secondary_project=str(secondary_project.uuid),
            )

            for queue in queues:
                # Check if already integrated
                if self._check_queue_exists(str(queue.uuid)):
                    logger.info(f"Queue {queue.uuid} already integrated, skipping")
                    skipped_count += 1
                    continue

                content = {
                    "uuid": str(queue.uuid),
                    "name": queue.name,
                    "sector_uuid": str(queue.sector.uuid),
                    "project_uuid": str(secondary_project.uuid),
                }

                try:
                    response = self.flows_client.create_queue(**content)

                    if response.status_code in [
                        status.HTTP_200_OK,
                        status.HTTP_201_CREATED,
                    ]:
                        self._mark_queue_integrated(str(queue.uuid))
                        integrated_count += 1
                        logger.info(f"Successfully integrated queue {queue.uuid}")
                    else:
                        raise exceptions.APIException(
                            detail=(
                                f"[{response.status_code}] Error posting the queue on flows. "
                                f"Exception: {response.content}"
                            )
                        )

                except Exception as e:
                    logger.error(f"Error integrating queue {queue.uuid}: {e}")
                    raise

        logger.info(
            f"Queue integration completed: {integrated_count} integrated, {skipped_count} skipped"
        )
        return {"integrated": integrated_count, "skipped": skipped_count}

    def integrate_individual_ticketer(self, project, integrated_token):
        """Integrate a specific individual ticketer."""
        try:
            sector = Sector.objects.get(
                project=project, config__secondary_project=str(integrated_token)
            )

            # Check if already integrated
            if self._check_ticketer_exists(str(sector.uuid)):
                logger.info(
                    f"Ticketer for sector {sector.uuid} already integrated, skipping"
                )
                return {"status": "skipped", "reason": "already_integrated"}

            content = {
                "project_uuid": str(sector.config.get("secondary_project")),
                "name": sector.name,
                "config": {
                    "project_auth": str(sector.external_token.pk),
                    "sector_uuid": str(sector.uuid),
                },
            }

            response = self.flows_client.create_ticketer(**content)

            if response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]:
                self._mark_ticketer_integrated(str(sector.uuid))
                logger.info(
                    f"Successfully integrated individual ticketer for sector {sector.uuid}"
                )
                return {"status": "success"}
            else:
                raise exceptions.APIException(
                    detail=(
                        f"[{response.status_code}] Error posting the sector/ticketer "
                        f"on flows. Exception: {response.content}"
                    )
                )

        except Sector.MultipleObjectsReturned:
            raise exceptions.APIException(
                detail=(
                    "Error posting the sector/ticketer on flows. There is more than one "
                    "sector with the same secondary project"
                )
            )

        except Exception as e:
            logger.error(f"Error integrating individual ticketer: {e}")
            raise exceptions.APIException(
                detail=f"There is no secondary project for that sector. Error: {e}"
            )

    def integrate_individual_topic(self, project, sector_integrated_token):
        """Integrate all queues from a specific sector."""
        try:
            queues = Queue.objects.filter(
                sector__project=project,
                sector__config__secondary_project=str(sector_integrated_token),
            )

            integrated_count = 0
            skipped_count = 0

            for queue in queues:
                # Check if already integrated
                if self._check_queue_exists(str(queue.uuid)):
                    logger.info(f"Queue {queue.uuid} already integrated, skipping")
                    skipped_count += 1
                    continue

                content = {
                    "uuid": str(queue.uuid),
                    "name": queue.name,
                    "sector_uuid": str(queue.sector.uuid),
                    "project_uuid": str(queue.sector.config.get("secondary_project")),
                }

                try:
                    response = self.flows_client.create_queue(**content)

                    if response.status_code in [
                        status.HTTP_200_OK,
                        status.HTTP_201_CREATED,
                    ]:
                        self._mark_queue_integrated(str(queue.uuid))
                        integrated_count += 1
                        logger.info(
                            f"Successfully integrated individual queue {queue.uuid}"
                        )
                    else:
                        raise exceptions.APIException(
                            detail=(
                                f"[{response.status_code}] Error posting the queue on flows. "
                                f"Exception: {response.content}"
                            )
                        )

                except Exception as e:
                    logger.error(
                        f"Error integrating individual queue {queue.uuid}: {e}"
                    )
                    raise

            logger.info(
                f"Individual queue integration completed: {integrated_count} integrated, {skipped_count} skipped"
            )
            return {"integrated": integrated_count, "skipped": skipped_count}

        except Exception as e:
            logger.error(f"Error in individual topic integration: {e}")
            raise exceptions.APIException(
                detail=f"There is no secondary project for that queue. Error: {e}"
            )
