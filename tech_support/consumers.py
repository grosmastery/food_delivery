import json

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer

from app.models import Messages, Room


class TechSupportChatConsumer(WebsocketConsumer):
    def connect(self):
        self.user = self.scope['user']
        self.room_id = self.scope['url_route']['kwargs']['room_id']

        if not self.user.is_authenticated or not Room.objects.filter(id=self.room_id).exists():
            self.close()
            return

        self.group_name = f'room_{self.room_id}'

        async_to_sync(self.channel_layer.group_add)(self.group_name, self.channel_name)

        self.accept()

    def disconnect(self, code):
        if hasattr(self, 'group_name'):
            async_to_sync(self.channel_layer.group_discard)(self.group_name, self.channel_name)

    def receive(self, text_data=None, bytes_data=None):
        data = json.loads(text_data)

        user = self.user.username
        if data['type'] == 'connected':
            async_to_sync(self.channel_layer.group_send)(
                self.group_name, {'type': 'chat_connected', 'message': f"{user} is joined to chat"}
            )
        else:
            Messages.objects.create(from_user=self.user, message=data['message'], room_id=self.room_id)
            async_to_sync(self.channel_layer.group_send)(
                self.group_name,
                {'type': 'chat_message', 'message': json.dumps({'text': data['message'], 'username': user})},
            )

    def chat_connected(self, event):
        message = event['message']

        self.send(text_data=json.dumps({'message': message, 'type': 'connected'}))

    def chat_message(self, event):
        message = event['message']

        self.send(
            text_data=json.dumps(
                {
                    'message': message,
                    'type': "message",
                }
            )
        )
