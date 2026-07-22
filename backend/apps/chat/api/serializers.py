from rest_framework import serializers


class StartConversationSerializer(serializers.Serializer):
    other_user_id = serializers.UUIDField()


class MessageSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    conversation_id = serializers.UUIDField()
    sender_id = serializers.UUIDField()
    sender_username = serializers.CharField()
    body = serializers.CharField()
    created_at = serializers.DateTimeField()


class ConversationSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    participant_ids = serializers.ListField(child=serializers.UUIDField())
    project_id = serializers.UUIDField(allow_null=True)
    created_at = serializers.DateTimeField()
    last_message = MessageSerializer(allow_null=True)


class SendMessageSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=4000)
