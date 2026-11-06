import time
from unittest.mock import MagicMock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from app.models import Cart, CartItem, Messages, Product, ProductCategory, Room
from app.views import CategoryView, CheckoutView, SuccessView


class SignUpViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.username = 'test'
        self.first_name = 'test'
        self.last_name = 'test'
        self.password = 'test'
        self.phone_number = 1234567890

    def test_diagnostic(self):
        response = self.client.get('/signup/')
        self.assertTrue(response.status_code != 404)

    def test_diagnostic_get(self):
        response = self.client.get('/signup/')
        self.assertTrue(response.status_code == 200)

    def test_signup_form_success(self):
        response = self.client.post(
            '/signup/',
            data={
                'username': self.username,
                'first_name': self.first_name,
                'last_name': self.last_name,
                'password': self.password,
                'check_password': self.password,
                'phone_number': self.phone_number,
            },
        )
        self.assertEqual(302, response.status_code)

    def test_signup_form_decline(self):
        response = self.client.post(
            '/signup/',
            data={
                'username': self.username,
                'first_name': self.first_name,
                'last_name': self.last_name,
                'password': self.password,
                'check_password': f'{self.password}0',
                'phone_number': self.phone_number,
            },
        )
        self.assertEqual(200, response.status_code)


class UserPageTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()
        self.user = get_user_model().objects.create_user(username='test', password='test')
        self.client.login(username='test', password='test')

    def test_diagnostic(self):
        response = self.client.get(f'/{self.user.slug}/profile/')
        self.assertTrue(response.status_code != 404)

    def test_diagnostic_get(self):
        response = self.client.get(f'/{self.user.slug}/profile/')
        self.assertTrue(response.status_code == 200)


class UpdateUserTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(username='test', password='test')
        self.client.login(username='test', password='test')

    def test_diagnostic(self):
        response = self.client.get(f'/{self.user.slug}/profile/update/')
        self.assertTrue(response.status_code != 404)

    def test_diagnostic_get(self):
        response = self.client.get(f'/{self.user.slug}/profile/update/')
        self.assertTrue(response.status_code == 200)

    def test_success(self):
        response = self.client.post(
            f'/{self.user.slug}/profile/update/',
            data={
                'username': 'test',
                'first_name': 'test',
                'last_name': 'test',
                'phone_number': 1234567890,
            },
        )
        self.assertEqual(302, response.status_code)


class OrderHistoryTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(username='test', password='test')
        self.client.login(username='test', password='test')
        self.user.session_key = self.user.get_session_auth_hash()

    def test_diagnostic(self):
        response = self.client.get(f'/{self.user.username}/profile/order-history/')
        self.assertTrue(response != 404)

    def test_diagnostic_get(self):
        response = self.client.get(f'/{self.user.username}/profile/order-history/')
        self.assertTrue(response.status_code == 200)

    def test_queryset(self):
        expected_result = 'test || True'
        ProductCategory.objects.create(category='test')
        Product.objects.create(title='test', price=10, category_id=1)
        cart = Cart.objects.create(session_key=self.user.session_key, ordered=True, user_id=self.user.id)
        CartItem.objects.create(cart=cart, item_id=1, quantity=1)
        response = self.client.get(f'/{self.user.username}/profile/order-history/')
        self.assertEqual(expected_result, str(response.context_data['object_list'][0]))


class CategoryTestCase(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        self.factory = RequestFactory()

    def test_diagnostic(self):
        response = self.client.get('/category/')
        self.assertTrue(response != 404)

    def test_diagnostic_get(self):
        response = self.client.get('/category/')
        self.assertTrue(response.status_code == 200)

    def test_get_rating(self):
        expected_result = ['test5', 'test4', 'test3', 'test2']
        ProductCategory.objects.create(category='test')
        for item in range(1, 6):
            Product.objects.create(title=f'test{item}', rating=item, category_id=1, price=1)
        request = self.factory.get('/category/')
        request.user = AnonymousUser()
        response = CategoryView.as_view()(request)
        result = response.context_data['items_rating'].values_list('title', flat=True)
        self.assertEqual(expected_result, list(result))


class ProductTestCase(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        self.category = ProductCategory.objects.create(category='test', slug='test')
        self.product = Product.objects.create(title='test', price=1, category_id=1)

    def test_diagnostic(self):
        response = self.client.get(f'/category/{self.category.slug}/')
        self.assertTrue(response != 404)

    def test_diagnostic_get(self):
        response = self.client.get(f'/category/{self.category.slug}/')
        self.assertTrue(response.status_code == 200)

    def test_get_queryset(self):
        expected_result = 'test'
        response = self.client.get(f'/category/{self.category.slug}/')
        result = response.context_data['object_list'][0]
        self.assertEqual(expected_result, str(result))


class AddToCardTestCase(TestCase):
    def setUp(self) -> None:
        self.client = Client()

    def test_diagnostic(self):
        response = self.client.get(reverse('add_to_cart'))
        self.assertTrue(response != 404)

    def test_create_cart_anonymous(self):
        expected_result = 'test || 1'
        ProductCategory.objects.create(category='test')
        Product.objects.create(title='test', price=1, category_id=1)

        self.client.post(reverse('add_to_cart'), {'item_id': 1})
        result = Cart.objects.get(id=1)
        self.assertEqual(expected_result, str(result.items.all().first()))

    def test_create_cart_logged_user(self):
        self.user = get_user_model().objects.create_user(username='test', password='test')
        self.client.login(username='test', password='test')

        expected_result = 'test || 1'
        ProductCategory.objects.create(category='test')
        Product.objects.create(title='test', price=1, category_id=1)

        self.client.post(reverse('add_to_cart'), {'item_id': 1})
        result = Cart.objects.get(id=1)
        self.assertEqual(expected_result, str(result.items.all().first()))

    def test_add_to_cart(self):
        expected_result = 'test || 2'
        ProductCategory.objects.create(category='test')
        Product.objects.create(title='test', price=1, category_id=1)

        [self.client.post(reverse('add_to_cart'), {'item_id': 1}) for _ in range(2)]
        result = Cart.objects.get(id=1)
        self.assertEqual(expected_result, str(result.items.all().first()))

    def test_add_to_cart_two_dif_products(self):
        expected_result = ['test', 'test2']
        ProductCategory.objects.create(category='test')
        Product.objects.create(title='test', price=1, category_id=1)
        Product.objects.create(title='test2', price=1, category_id=1)

        self.client.post(reverse('add_to_cart'), {'item_id': 1})
        self.client.post(reverse('add_to_cart'), {'item_id': 2})
        result = Cart.objects.get(id=1).items.all().values_list('item__title', flat=True)
        self.assertEqual(expected_result, list(result))


class DeleteElementFromCartTestCase(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        ProductCategory.objects.create(category='test')
        Product.objects.create(title='test', price=1, category_id=1)
        Product.objects.create(title='test2', price=1, category_id=1)

        self.client.post(reverse('add_to_cart'), {'item_id': 1})

    def test_diagnostic(self):
        response = self.client.get(reverse('del_element_from_cart'))
        self.assertTrue(response != 404)

    def test_delete_item(self):
        expected_result = 'test2 || 1'

        self.client.post(reverse('add_to_cart'), {'item_id': 2})
        self.client.post(reverse('del_element_from_cart'), {'del_item': 1})

        result = Cart.objects.get(id=1).items.all()[0]
        self.assertEqual(expected_result, str(result))

    def test_delete_all_items(self):
        self.client.post(reverse('del_element_from_cart'), {'del_item': 1})
        result = Cart.objects.all().first()
        self.assertTrue(result is None)


class DeleteAllElementsFromCartTestCase(TestCase):
    def setUp(self) -> None:
        self.client = Client()

        ProductCategory.objects.create(category='test')
        Product.objects.create(title='test', price=1, category_id=1)
        Product.objects.create(title='test2', price=1, category_id=1)

        self.client.post(reverse('add_to_cart'), {'item_id': 1})
        self.client.post(reverse('add_to_cart'), {'item_id': 2})

    def test_diagnostic(self):
        response = self.client.get(reverse('del_all_elements_from_cart'))
        self.assertTrue(response != 404)

    def test_del_all_items(self):
        self.client.post(reverse('del_all_elements_from_cart'), {'cart_id': 1})
        result = Cart.objects.all().first()
        self.assertTrue(result is None)


class CheckoutTestCase(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        self.factory = RequestFactory()

        self.user = get_user_model().objects.create_user(username='test', password='test')
        self.user.first_name = 'testname'
        self.user.last_name = 'testlastname'
        self.user.address = 'test address'
        self.user.phone_number = 1234567890
        ProductCategory.objects.create(category='test')
        Product.objects.create(title='test', price=100, category_id=1)

    def test_diagnostic(self):
        response = self.client.get(reverse('checkout'))
        self.assertTrue(response != 404)

    def test_get_context_data_anonymous(self):
        request = self.factory.get(reverse('checkout'))
        request.user = AnonymousUser()
        request.session = MagicMock(return_value='test_session_key')
        response = CheckoutView.as_view()(request)
        self.assertEqual('/cart/', response.url)

    def test_get_context_data(self):
        self.user.bonus_coins = 100
        self.client.login(username='test', password='test')
        self.client.post(reverse('add_to_cart'), {'item_id': 1})
        request = self.factory.get(reverse('checkout'))
        request.user = self.user
        request.session = MagicMock(return_value='test_session_key')
        response = CheckoutView.as_view()(request)

        first_name = response.context_data['form']['first_name'].value()
        last_name = response.context_data['form']['last_name'].value()
        address = response.context_data['form']['address'].value()
        phone_number = response.context_data['form']['phone_number'].value()

        self.assertEqual(self.user.first_name, first_name)
        self.assertEqual(self.user.last_name, last_name)
        self.assertEqual(self.user.address, address)
        self.assertEqual(self.user.phone_number, phone_number)
        self.assertTrue(response.context_data['bonus_c'] is True)

    def test_post_cash(self):
        expected_result = '/success/'
        self.client.post(reverse('add_to_cart'), {'item_id': 1})
        response = self.client.post(
            reverse('checkout'),
            {
                'first_name': 'testname',
                'last_name': 'testlastname',
                'address': 'test address',
                'phone_number': 1234567890,
                'payment_choice': 'Cash',
            },
        )
        self.assertEqual(expected_result, response.url)

    def test_post_cash_accrual_coins(self):
        expected_result = 1.0
        self.client.login(username='test', password='test')
        self.client.post(reverse('add_to_cart'), {'item_id': 1})
        request = self.factory.post(
            reverse('checkout'),
            {
                'first_name': 'testname',
                'last_name': 'testlastname',
                'address': 'test address',
                'phone_number': 1234567890,
                'payment_choice': 'Cash',
            },
        )
        middleware = SessionMiddleware(request)
        middleware.process_request(request)
        request.session.save()
        request.user = self.user
        CheckoutView.as_view()(request)
        self.assertEqual(expected_result, self.user.bonus_coins)

    def test_post_bonus_coins(self):
        expected_result = '/success/'
        expected_result_balance = 0
        self.user.bonus_coins = 100
        self.user.save()
        self.client.login(username='test', password='test')
        self.client.post(reverse('add_to_cart'), {'item_id': 1})
        request = self.factory.post(
            reverse('checkout'),
            {
                'first_name': 'testname',
                'last_name': 'testlastname',
                'address': 'test address',
                'phone_number': 1234567890,
                'payment_choice': 'Bonus coins',
            },
        )
        middleware = SessionMiddleware(request)
        middleware.process_request(request)
        request.session.save()
        request.user = self.user
        response = CheckoutView.as_view()(request)
        self.assertEqual(expected_result_balance, self.user.bonus_coins)
        self.assertEqual(expected_result, response.url)

    def test_post_card(self):
        expected_result = '/create-charge/'
        self.client.post(reverse('add_to_cart'), {'item_id': 1})
        response = self.client.post(
            reverse('checkout'),
            {
                'first_name': 'testname',
                'last_name': 'testlastname',
                'address': 'test address',
                'phone_number': 1234567890,
                'payment_choice': 'Card',
            },
        )
        self.assertEqual(expected_result, response.url)

    def test_post_error(self):
        self.client.post(reverse('add_to_cart'), {'item_id': 1})
        response = self.client.post(reverse('checkout'))
        self.assertEqual(200, response.status_code)


class ChargeTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()

        self.user = get_user_model().objects.create_user(username='test', password='test')
        self.user.first_name = 'testname'
        self.user.last_name = 'testlastname'
        self.user.address = 'test address'
        self.user.phone_number = 1234567890
        ProductCategory.objects.create(category='test')
        Product.objects.create(title='test', price=100, category_id=1)

    def test_diagnostic(self):
        response = self.client.get(reverse('create-charge'))
        self.assertTrue(response != 404)

    def test_get_context_data_anonymous(self):
        self.client.post(reverse('add_to_cart'), {'item_id': 1})
        response = self.client.get(reverse('create-charge'))
        self.assertTrue(response.status_code == 200)

    def test_get_context_data(self):
        self.client.login(username='test', password='test')
        self.client.post(reverse('add_to_cart'), {'item_id': 1})
        response = self.client.get(reverse('create-charge'))
        self.assertTrue(response.status_code == 200)


class SuccessTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()

        ProductCategory.objects.create(category='test')
        for item in range(1, 7):
            Product.objects.create(title=f'test{item}', category_id=1, price=item, added=item)
            time.sleep(0.001)

    def test_diagnostic(self):
        response = self.client.get(reverse('success'))
        self.assertTrue(response != 404)

    def test_get_context_data(self):
        success_result = ['test6', 'test5', 'test4', 'test3', 'test2']
        request = self.factory.get('/success/')
        request.user = AnonymousUser()
        response = SuccessView.as_view()(request)
        result = response.context_data['new_items'].values_list('title', flat=True)
        self.assertEqual(success_result, list(result))


class RoomListTestCase(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        Room.objects.create(room_name='test')

    def test_diagnostic(self):
        response = self.client.get(reverse('room_list'))
        self.assertTrue(response != 404)

    def test_queryset(self):
        expected_result = 'test'
        response = self.client.get(reverse('room_list'))
        result = response.context_data['object_list'][0]
        self.assertEqual(expected_result, str(result))


class TechSupportTestCase(TestCase):
    def setUp(self) -> None:
        self.client = Client()

        self.user = get_user_model().objects.create_user(username='test', password='test')
        Room.objects.create(room_name='room_test')
        Messages.objects.create(room_id=1, from_user_id=1, message='test_message')

    def test_diagnostic(self):
        response = self.client.get('/tech-support/1/')
        self.assertTrue(response.status_code != 404)

    def test_get_context_data_room(self):
        expected_result = 'room_test'
        response = self.client.get('/tech-support/1/')
        result = response.context_data['room']
        self.assertEqual(expected_result, str(result))

    def test_get_context_data_message(self):
        expected_result = 'test'
        response = self.client.get('/tech-support/1/')
        result = response.context_data['message'][0]
        self.assertEqual(expected_result, str(result))
