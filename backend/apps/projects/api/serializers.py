from rest_framework import serializers


class ProjectUploadSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(max_length=2000, required=False, allow_blank=True, default="")
    file = serializers.FileField()


class ProjectSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    description = serializers.CharField()
    file_name = serializers.CharField()
    file_size = serializers.IntegerField()
    content_type = serializers.CharField()
    status = serializers.CharField()
    download_count = serializers.IntegerField()
    created_at = serializers.DateTimeField()
