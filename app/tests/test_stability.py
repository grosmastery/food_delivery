import re
from unittest.mock import patch

import stripe
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from app.forms import CheckoutForm
from app.models import Cart, Product, ProductCategory
from app.tests.stripe_objects import card_list

CHECKOUT_DATA = {
    'first_name': 'testname',
    'last_name': 'testlastname',
    'address': 'test address',
    'phone_number': '0671234567',
    'payment_choice': 'Cash',
}


class LoginRequiredTestCase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='test', password='test')
        self.client = Client()

    def test_anonymous_redirected_to_login(self):
        for url in (f'/{self.user.slug}/profile/', '/update-card/', f'/{self.user.slug}/profile/order-history/'):
            response = self.client.get(url)
            self.assertEqual(302, response.status_code, url)
            self.assertTrue(response.url.startswith('/login/'), url)

    @patch('stripe.Customer.list_payment_methods', return_value=card_list())
    def test_profile_when_default_card_was_removed(self, list_sources):
        self.user.default_card = True
        self.user.save()
        self.client.login(username='test', password='test')
        self.assertEqual(200, self.client.get(f'/{self.user.slug}/profile/').status_code)


class EmptyCartTestCase(TestCase):
    def setUp(self):
        get_user_model().objects.create_user(username='test', password='test')
        self.client = Client()
        self.client.login(username='test', password='test')

    def test_checkout_redirects_to_cart(self):
        self.assertEqual('/cart/', self.client.get(reverse('checkout')).url)

    def test_charge_redirects_to_cart(self):
        self.assertEqual('/cart/', self.client.get(reverse('create-charge')).url)


class CartOwnershipTestCase(TestCase):
    def setUp(self):
        category = ProductCategory.objects.create(category='test')
        self.pizza = Product.objects.create(title='pizza', price=10, category=category)
        self.cola = Product.objects.create(title='cola', price=2, category=category)
        self.user = get_user_model().objects.create_user(username='test', password='test')
        self.client = Client()

    def add(self, product):
        self.client.post(reverse('add_to_cart'), {'item_id': product.id})

    def test_anonymous_cart_moves_to_user_on_login(self):
        self.add(self.pizza)
        self.client.login(username='test', password='test')
        cart = Cart.objects.get()
        self.assertEqual(self.user, cart.user)
        self.assertEqual(200, self.client.get(reverse('checkout')).status_code)

    def test_anonymous_cart_merges_into_user_cart(self):
        self.client.login(username='test', password='test')
        self.add(self.pizza)
        self.client.logout()
        self.add(self.pizza)
        self.add(self.cola)
        self.client.login(username='test', password='test')

        cart = Cart.objects.get()
        items = {i.item.title: i.quantity for i in cart.items.all()}
        self.assertEqual({'pizza': 2, 'cola': 1}, items)

    def test_cart_survives_password_change(self):
        self.client.login(username='test', password='test')
        self.add(self.pizza)
        self.user.set_password('new-password')
        self.user.save()
        self.client.login(username='test', password='new-password')
        self.assertEqual(200, self.client.get(reverse('checkout')).status_code)

    def test_order_history_survives_password_change(self):
        self.client.login(username='test', password='test')
        self.add(self.pizza)
        self.client.post(reverse('checkout'), CHECKOUT_DATA)
        self.user.set_password('new-password')
        self.user.save()
        self.client.login(username='test', password='new-password')
        response = self.client.get(f'/{self.user.slug}/profile/order-history/')
        self.assertEqual(1, len(response.context_data['object_list']))


class CheckoutFormValidationTestCase(TestCase):
    def form(self, **data):
        return CheckoutForm(data={**CHECKOUT_DATA, **data})

    def test_phone_with_leading_zero(self):
        form = self.form(phone_number='0671234567')
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual('0671234567', form.cleaned_data['phone_number'])

    def test_invalid_phones(self):
        for phone in ('067123456', '06712345678', '067123456a', ''):
            self.assertIn('phone_number', self.form(phone_number=phone).errors, phone)

    def test_names_with_hyphen_and_apostrophe(self):
        form = self.form(first_name='Анна-Марія', last_name="Мар'яненко")
        self.assertTrue(form.is_valid(), form.errors)

    def test_invalid_names(self):
        for name in ('Anna1', '-Anna', "Anna''", 'Anna--Maria'):
            self.assertIn('first_name', self.form(first_name=name).errors, name)


class TechSupportRoomTestCase(TestCase):
    def test_unknown_room_is_404(self):
        self.assertEqual(404, Client().get('/tech-support/999/').status_code)


class StripeErrorsTestCase(TestCase):
    def setUp(self):
        category = ProductCategory.objects.create(category='test')
        pizza = Product.objects.create(title='pizza', price=10, category=category)
        self.client = Client()
        self.client.post(reverse('add_to_cart'), {'item_id': pizza.id})

    @patch('stripe.PaymentIntent.create', side_effect=stripe.APIConnectionError('down'))
    def test_generic_stripe_error_handled(self, intent_create):
        response = self.client.post(reverse('create-charge'), {'payment_method_id': 'pm_card_visa'})
        self.assertEqual(502, response.status_code)
        self.assertIn('error', response.json())
        self.assertFalse(Cart.objects.get().ordered)


class LogoutTestCase(TestCase):
    def setUp(self):
        get_user_model().objects.create_user(username='test', password='test')
        self.client = Client()
        self.client.login(username='test', password='test')

    def test_logout_form_is_not_nested(self):
        html = self.client.get('/').content.decode()
        navbar = html[html.index('<nav') : html.index('</nav>')]
        depth = 0
        for tag in re.findall(r'<(/?)form\b', navbar):
            depth += -1 if tag else 1
            self.assertIn(depth, (0, 1))
        self.assertEqual(0, depth)
        self.assertIn('action="/logout/"', navbar)

    def test_logout_with_post(self):
        self.assertEqual(405, self.client.get('/logout/').status_code)
        self.client.post('/logout/')
        self.assertNotIn('_auth_user_id', self.client.session)
