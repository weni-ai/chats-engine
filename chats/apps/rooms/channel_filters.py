from django.db.models import Q

CHANNEL_URN_PREFIXES = {
    "instagram": ("instagram:",),
    "facebook": ("facebook:",),
    "whatsapp": ("whatsapp:",),
    "teams": ("teams:", "msteams:"),
    "email": ("email:", "mailto:"),
    "shopping_assistant": ("ext:", "shopping_assistant:"),
}

KNOWN_URN_PREFIXES = tuple(
    prefix for prefixes in CHANNEL_URN_PREFIXES.values() for prefix in prefixes
)
VALID_CHANNELS = frozenset(CHANNEL_URN_PREFIXES) | {"others"}


def channel_name_from_urn(urn) -> str:
    if not urn:
        return "others"
    urn = str(urn)
    for channel, prefixes in CHANNEL_URN_PREFIXES.items():
        for prefix in prefixes:
            if urn.startswith(prefix):
                return channel
    return "others"


def normalize_channels(value):
    if value is None or value == "":
        return None
    if isinstance(value, str):
        items = value.split(",")
    else:
        items = []
        for entry in value:
            items.extend(str(entry).split(","))
    channels = [item.strip() for item in items if item and str(item).strip()]
    return channels or None


def channels_q(channels, urn_field="urn"):
    channels = normalize_channels(channels)
    if not channels:
        return None

    combined = Q()
    has_clause = False
    startswith = f"{urn_field}__startswith"

    for channel in channels:
        if channel not in VALID_CHANNELS:
            continue
        has_clause = True
        if channel == "others":
            known = Q()
            for prefix in KNOWN_URN_PREFIXES:
                known |= Q(**{startswith: prefix})
            combined |= ~known
            continue
        part = Q()
        for prefix in CHANNEL_URN_PREFIXES[channel]:
            part |= Q(**{startswith: prefix})
        combined |= part

    return combined if has_clause else None


def merge_channels_q(base_filter, channels, urn_field="urn"):
    channel_filter = channels_q(channels, urn_field=urn_field)
    if channel_filter is None:
        return base_filter
    return base_filter & channel_filter


def apply_channels_filter(queryset, channels, urn_field="urn"):
    channel_filter = channels_q(channels, urn_field=urn_field)
    if channel_filter is None:
        return queryset
    return queryset.filter(channel_filter)
