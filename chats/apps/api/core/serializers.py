from rest_framework import serializers


class CommaSeparatedListField(serializers.ListField):
    """Accepts a comma-separated query string or a list of values."""

    def to_internal_value(self, data):
        if data is None or data == "":
            return []
        if isinstance(data, str):
            data = [item.strip() for item in data.split(",") if item.strip()]
        elif isinstance(data, (list, tuple)):
            expanded = []
            for item in data:
                if isinstance(item, str):
                    expanded.extend(
                        part.strip() for part in item.split(",") if part.strip()
                    )
                elif item is not None and item != "":
                    expanded.append(item)
            data = expanded
        return super().to_internal_value(data)
