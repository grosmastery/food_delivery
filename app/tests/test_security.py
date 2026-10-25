from channels.db import database_sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase, TransactionTestCase, Client, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from app.models import Cart, Product, ProductCategory, Room, Messages
from tech_support.routing import ws_routes


class UpdateUserSecurityTestCase(TestCase):

    def setUp(self):
        self.client = Client()
        self.victim = get_user_model().objects.create_user(username='victim', password='test', email='v@test.com')
        self.attacker = get_user_model().objects.create_user(username='attacker', password='test')

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(f'/{self.victim.slug}/profile/update/')
        self.assertEqual(302, response.status_code)
        self.assertTrue(response.url.startswith('/login/'))

    def test_cannot_update_other_user(self):
        self.client.login(username='attacker', password='test')
        self.client.post(f'/{self.victim.slug}/profile/update/', data={
            'username': 'attacker',
            'first_name': 'test',
            'last_name': 'test',
            'phone_number': 1234567890,
            'email': 'hacked@test.com',
        })
        self.victim.refresh_from_db()
        self.assertEqual('v@test.com', self.victim.email)


class CartSecurityTestCase(TestCase):

    def setUp(self):
        ProductCategory.objects.create(category='test')
        Product.objects.create(title='test', price=1, category_id=1)
        self.owner = Client()
        self.owner.post(reverse('add_to_cart'), {'item_id': 1})
        self.cart = Cart.objects.get()
        self.item = self.cart.items.get()
        self.stranger = Client()

    def test_cannot_delete_other_cart(self):
        response = self.stranger.post(reverse('del_all_elements_from_cart'), {'cart_id': self.cart.id})
        self.assertEqual(404, response.status_code)
        self.assertTrue(Cart.objects.filter(id=self.cart.id).exists())

    def test_cannot_delete_item_from_other_cart(self):
        response = self.stranger.post(reverse('del_element_from_cart'), {'del_item': self.item.id})
        self.assertEqual(404, response.status_code)
        self.assertTrue(self.cart.items.filter(id=self.item.id).exists())


class UserApiSecurityTestCase(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(username='user', password='test')
        self.other = get_user_model().objects.create_user(username='other', password='test')
        self.client.force_authenticate(self.user)

    def test_list_contains_only_self(self):
        response = self.client.get('/api/users/')
        self.assertEqual(['user'], [u['username'] for u in response.data])

    def test_cannot_read_other_user(self):
        response = self.client.get(f'/api/users/{self.other.id}/')
        self.assertEqual(404, response.status_code)

    def test_cannot_escalate_privileges(self):
        self.client.patch(f'/api/users/{self.user.id}/', {
            'is_superuser': True, 'is_staff': True, 'bonus_coins': 1000, 'stripe_customer_id': 'cus_other',
        })
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_superuser)
        self.assertFalse(self.user.is_staff)
        self.assertEqual(0, self.user.bonus_coins)
        self.assertIsNone(self.user.stripe_customer_id)

    def test_cannot_delete_users(self):
        response = self.client.delete(f'/api/users/{self.user.id}/')
        self.assertEqual(403, response.status_code)


class ProductApiSecurityTestCase(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(username='user', password='test')
        self.admin = get_user_model().objects.create_user(username='admin', password='test', is_staff=True)
        self.category = ProductCategory.objects.create(category='test')
        self.product_data = {'title': 'new', 'compound': 'x', 'description': 'x', 'price': 1,
                             'category': self.category.id}

    def test_user_can_read_products(self):
        self.client.force_authenticate(self.user)
        self.assertEqual(200, self.client.get('/api/products/').status_code)

    def test_user_cannot_create_product(self):
        self.client.force_authenticate(self.user)
        response = self.client.post('/api/products/', self.product_data)
        self.assertEqual(403, response.status_code)

    def test_user_cannot_create_category(self):
        self.client.force_authenticate(self.user)
        response = self.client.post('/api/categories/', {'category': 'new'})
        self.assertEqual(403, response.status_code)

    def test_admin_can_create_product(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post('/api/products/', self.product_data)
        self.assertEqual(201, response.status_code)


@override_settings(CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}})
class TechSupportChatSecurityTestCase(TransactionTestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='user', password='test')
        self.other = get_user_model().objects.create_user(username='other', password='test')
        self.room = Room.objects.create(room_name='room')
        self.other_room = Room.objects.create(room_name='other_room')

    async def connect(self, user, room_id):
        communicator = WebsocketCommunicator(URLRouter(ws_routes), f'/ws/chat/{room_id}/')
        communicator.scope['user'] = user
        connected, _ = await communicator.connect()
        return communicator, connected

    async def test_anonymous_rejected(self):
        communicator, connected = await self.connect(AnonymousUser(), self.room.id)
        self.assertFalse(connected)

    async def test_unknown_room_rejected(self):
        communicator, connected = await self.connect(self.user, 999)
        self.assertFalse(connected)

    async def test_message_author_and_room_come_from_server(self):
        communicator, connected = await self.connect(self.user, self.room.id)
        self.assertTrue(connected)
        await communicator.send_json_to({
            'type': 'message', 'message': 'hi', 'user_id': self.other.id, 'room_id': self.other_room.id,
        })
        await communicator.receive_json_from()
        await communicator.disconnect()

        message = await database_sync_to_async(Messages.objects.get)()
        self.assertEqual(self.user.id, message.from_user_id)
        self.assertEqual(self.room.id, message.room_id)

    async def test_rooms_are_isolated(self):
        sender, _ = await self.connect(self.user, self.room.id)
        listener, _ = await self.connect(self.other, self.other_room.id)
        await sender.send_json_to({'type': 'message', 'message': 'hi'})
        await sender.receive_json_from()
        self.assertTrue(await listener.receive_nothing())
        await sender.disconnect()
        await listener.disconnect()
