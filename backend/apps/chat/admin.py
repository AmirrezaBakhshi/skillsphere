from django.contrib import admin

from apps.chat.infrastructure.django.models import Conversation, Message


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "created_at")
    filter_horizontal = ("participants",)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("conversation", "sender", "body", "created_at")
    search_fields = ("body", "sender__username")
