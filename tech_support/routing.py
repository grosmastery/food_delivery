from django.urls import path

from tech_support import consumers

ws_routes = {
    path('ws/chat/<int:room_id>/', consumers.TechSupportChatConsumer.as_asgi())
}
