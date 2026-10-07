import uuid
from datetime import timedelta

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import Message
from chats.apps.projects.models import Project
from chats.apps.rooms.models import Room

WHATSAPP_RESPONSE_WINDOW_DAYS = 1


class InvalidOutOffWindowFilter(Exception):
    pass


class ProjectNotFound(Exception):
    pass


def get_project_for_user(project_uuid, user):
    try:
        project = Project.objects.get(uuid=project_uuid)
        project.permissions.get(user=user)
        return project
    except (Project.DoesNotExist, ObjectDoesNotExist, ValidationError, ValueError):
        raise ProjectNotFound()


def parse_csv(value):
    if not value:
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]


def _parse_uuids(values, field_name):
    parsed = []
    for value in values or []:
        try:
            parsed.append(uuid.UUID(str(value)))
        except (ValueError, AttributeError, TypeError):
            raise InvalidOutOffWindowFilter(f"Invalid {field_name}.")
    return parsed


def out_off_whatsapp_response_window(project, sectors=None, queues=None, search=None):
    """Rooms outside the WhatsApp 24h window, and the contacts that own them."""
    cutoff = timezone.now() - timedelta(days=WHATSAPP_RESPONSE_WINDOW_DAYS)
    recent_contact_message = Message.objects.filter(
        room_id=OuterRef("pk"),
        contact_id=OuterRef("contact_id"),
        created_on__gte=cutoff,
    )
    rooms = Room.objects.filter(
        queue__sector__project=project,
        urn__startswith="whatsapp",
        created_on__lte=cutoff,
        contact__isnull=False,
    ).exclude(Exists(recent_contact_message))

    sector_ids = _parse_uuids(sectors, "sectors")
    queue_ids = _parse_uuids(queues, "queues")
    if sector_ids:
        rooms = rooms.filter(queue__sector__uuid__in=sector_ids)
    if queue_ids:
        rooms = rooms.filter(queue__uuid__in=queue_ids)

    search = (search or "").strip()
    if search:
        rooms = rooms.filter(
            Q(contact__name__icontains=search)
            | Q(contact__email__icontains=search)
            | Q(urn__icontains=search)
        )

    contacts = (
        Contact.objects.filter(pk__in=rooms.values("contact_id"))
        .exclude(Q(external_id__isnull=True) | Q(external_id=""))
        .only("pk", "external_id", "name")
        .order_by("name", "uuid")
        .distinct()
    )
    return contacts, rooms


def build_out_off_window_contact_payload(contacts, rooms):
    contact_ids = [contact.pk for contact in contacts]
    urns_by_contact = {contact_id: [] for contact_id in contact_ids}
    seen = {contact_id: set() for contact_id in contact_ids}
    urn_rows = (
        rooms.filter(contact_id__in=contact_ids)
        .order_by("urn")
        .values_list("contact_id", "urn")
    )
    for contact_id, urn in urn_rows:
        if not urn or urn in seen[contact_id]:
            continue
        seen[contact_id].add(urn)
        scheme, _, path = urn.partition(":")
        urns_by_contact[contact_id].append({"scheme": scheme, "path": path})

    return [
        {
            "uuid": contact.external_id,
            "name": contact.name,
            "urns": urns_by_contact.get(contact.pk, []),
        }
        for contact in contacts
    ]
