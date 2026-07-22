from rest_framework import serializers


class ProjectRecommendationSerializer(serializers.Serializer):
    project_id = serializers.UUIDField()
    title = serializers.CharField()
    owner_username = serializers.CharField()
    shared_tags = serializers.ListField(child=serializers.CharField())
    score = serializers.FloatField()
    reason = serializers.CharField()
