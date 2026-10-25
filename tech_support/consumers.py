from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
import json
from app.models import Messages
from django.contrib.auth import get_user_model


class TechSupportChatConsumer(WebsocketConsumer):

    def connect(self):
        self.group_name = 'firstgroup'

        async_to_sync(self.channel_layer.group_add)(
            self.group_name,
            self.channel_name
        )

        self.accept()

    def disconnect(self, code):
        print('disconnected')
        pass

    def receive(self, text_data=None, bytes_data=None):
        data = json.loads(text_data)

        user = get_user_model().objects.get(id=data['user_id']).username
        if data['type'] == 'connected':
            async_to_sync(self.channel_layer.group_send)(
                self.group_name,
                {
                    'type': 'chat_connected',
                    'message': f"{user} is joined to chat"
                }
            )
        else:
            print(data)
            Messages.objects.create(from_user_id=data['user_id'], message=data['message'], room_id=data['room_id'])
            async_to_sync(self.channel_layer.group_send)(
                self.group_name,
                {
                    'type': 'chat_message',
                    'message': json.dumps({'text': data['message'], 'username': user})
                }

            )

    def chat_connected(self, event):
        message = event['message']

        self.send(text_data=json.dumps({
            'message': message,
            'type': 'connected'
        }))

    def chat_message(self, event):
        message = event['message']

        self.send(text_data=json.dumps({
            'message': message,
            'type': "message",
        }))
