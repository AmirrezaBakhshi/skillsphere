from rest_framework import serializers


class ActivityLogSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    action = serializers.CharField()
    path = serializers.CharField()
    method = serializers.CharField()
    status_code = serializers.IntegerField()
    created_at = serializers.DateTimeField()
