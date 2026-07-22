import uuid

from django.conf import settings
from django.db import models


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="conversations"
    )
    # Set when this conversation is scoped to discussing a specific project
    # (e.g. "message the owner about their upload") - null for a plain DM.
    project = models.ForeignKey(
        "projects.Project", on_delete=models.SET_NULL, null=True, blank=True, related_name="conversations"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "chat"
        db_table = "chat_conversation"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Conversation {self.id}"


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    body = models.TextField(max_length=4000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "chat"
        db_table = "chat_message"
        ordering = ["created_at"]
        indexes = [models.Index(fields=["conversation", "created_at"])]

    def __str__(self) -> str:
        return f"{self.sender_id} in {self.conversation_id}: {self.body[:30]}"
