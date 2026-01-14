def get_data_from_object(obj):
    data = {"type": "", "name": ""}

    if hasattr(obj, "_meta"):
        data["type"] = obj._meta.model_name

        fields = {"name", "uuid"}

        if data["type"] == "user":
            fields.add("id")
            fields.add("email")

        for field in fields:
            if value := getattr(obj, field, None):
                data[field] = str(value)

    return data


def create_transfer_json(action: str, from_, to, requested_by=None):
    source = requested_by if requested_by else from_
    from_data = get_data_from_object(source)
    to_data = get_data_from_object(to)

    feedback = {
        "action": action,
        "from": from_data,
        "to": to_data,
    }

    if requested_by:
        feedback["requested_by"] = get_data_from_object(requested_by)

    return feedback
