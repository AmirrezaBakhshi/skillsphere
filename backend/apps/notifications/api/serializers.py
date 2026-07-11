from rest_framework import serializers


class NotificationSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    verb = serializers.CharField()
    message = serializers.CharField()
    level = serializers.CharField()
    is_read = serializers.BooleanField()
    created_at = serializers.DateTimeField()
