from rest_framework import serializers


class ProjectSearchResultSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    description = serializers.CharField()
    tags = serializers.ListField(child=serializers.CharField())
    owner_username = serializers.CharField()
    score = serializers.FloatField()


class UserSearchResultSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    username = serializers.CharField()
    bio = serializers.CharField()
    score = serializers.FloatField()
