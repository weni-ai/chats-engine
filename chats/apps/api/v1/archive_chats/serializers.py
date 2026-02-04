from rest_framework import serializers


class GetArchivedMediaQueryParamsSerializer(serializers.Serializer):
    object_key = serializers.CharField(required=True)
