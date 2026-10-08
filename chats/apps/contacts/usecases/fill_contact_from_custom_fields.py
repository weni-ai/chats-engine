from typing import Any, Dict

from chats.apps.contacts.models import Contact, normalize_document

CUSTOM_FIELDS_CONTACT_KEYS = ("email", "document")


def get_contact_updates_from_custom_fields(
    contact: Contact, custom_fields: Any
) -> Dict[str, str]:
    """
    Returns email/document values to copy from room custom_fields onto a
    contact, only for fields that are currently empty.
    """
    if not isinstance(custom_fields, dict):
        return {}

    updates = {}
    for field in CUSTOM_FIELDS_CONTACT_KEYS:
        value = custom_fields.get(field)
        if getattr(contact, field) or not isinstance(value, str) or not value.strip():
            continue
        updates[field] = value.strip()

    if "document" in updates:
        updates["document"] = normalize_document(updates["document"])

    return updates
