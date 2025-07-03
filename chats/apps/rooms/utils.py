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


def create_transfer_json(action: str, from_, to):
    from_data = get_data_from_object(from_)
    to_data = get_data_from_object(to)

    return {
        "action": action,
        "from": from_data,
        "to": to_data,
    }
