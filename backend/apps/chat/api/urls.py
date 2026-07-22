from django.urls import path

from apps.chat.api.views import (
    ConversationMessagesView,
    MyConversationsView,
    StartConversationView,
)

app_name = "chat"

urlpatterns = [
    path("start/", StartConversationView.as_view(), name="start"),
    path("mine/", MyConversationsView.as_view(), name="mine"),
    path("<uuid:conversation_id>/messages/", ConversationMessagesView.as_view(), name="messages"),
]
