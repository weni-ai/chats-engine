from datetime import timedelta

from django.conf import settings
from django.contrib.postgres.expressions import ArraySubquery
from django.core.paginator import Paginator
from django.db.models import Count, F, OuterRef, Q
from django.db.models.functions import JSONObject
from django.utils import timezone

from chats.apps.projects.models import Project
from chats.apps.sectors.models import Sector
from chats.celery import app


@app.task(name="send_project_reports")
def send_project_reports():
    BATCH_SIZE = settings.REPORT_BATCH_SIZE
    yesterday = timezone.now().date() - timedelta(days=1)
    sector_subquery = (
        Sector.objects.only("project", "name")
        .filter(project=OuterRef("pk"))
        .order_by()
        .values("project")
        .annotate(
            data=JSONObject(
                name=F("name"),
                rooms_count=Count(
                    "queues__rooms",
                    distinct=True,
                    filter=Q(queues__rooms__created_on__date=yesterday),
                ),
                agents_count=Count("queues__authorizations", distinct=True),
            ),
        )
        .values_list("data", flat=True)
    )

    project_list = (
        Project.objects.only("uuid", "name")
        .annotate(sector_list=ArraySubquery(sector_subquery))
        .values("uuid", "name", "sector_list")
    )

    paginator = Paginator(project_list, BATCH_SIZE)
    for page in paginator.page_range:
        # TODO send data to the microsservice
        # MicrosserviceClient.send_project_metrics(paginator.page(page).object_list)
        ...
