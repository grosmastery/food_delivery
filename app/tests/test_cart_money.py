from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from app.models import Cart, CartItem, Product, ProductCategory

CHECKOUT_DATA = {
    'first_name': 'testname',
    'last_name': 'testlastname',
    'address': 'test address',
    'phone_number': 1234567890,
}


class CartTotalTestCase(TestCase):
    def setUp(self):
        category = ProductCategory.objects.create(category='test')
        self.pizza = Product.objects.create(title='pizza', price=Decimal('10.50'), category=category)
        self.cola = Product.objects.create(title='cola', price=Decimal('2.25'), category=category)
        self.client = Client()

    def test_total_includes_all_items(self):
        self.client.post(reverse('add_to_cart'), {'item_id': self.pizza.id})
        self.client.post(reverse('add_to_cart'), {'item_id': self.pizza.id})
        self.client.post(reverse('add_to_cart'), {'item_id': self.cola.id})
        cart = Cart.objects.get()
        self.assertEqual(Decimal('23.25'), cart.get_total())
        self.assertEqual(3, cart.items_counter())

    def test_empty_cart_total_is_zero(self):
        self.assertEqual(Decimal('0'), Cart.objects.create().get_total())


class SeparateCartItemsTestCase(TestCase):
    def setUp(self):
        category = ProductCategory.objects.create(category='test')
        self.pizza = Product.objects.create(title='pizza', price=10, category=category)
        self.first = Client()
        self.second = Client()
        self.first.post(reverse('add_to_cart'), {'item_id': self.pizza.id})
        self.second.post(reverse('add_to_cart'), {'item_id': self.pizza.id})
        self.second.post(reverse('add_to_cart'), {'item_id': self.pizza.id})

    def test_each_cart_has_own_items(self):
        quantities = sorted(CartItem.objects.values_list('quantity', flat=True))
        self.assertEqual([1, 2], quantities)

    def test_delete_does_not_touch_other_cart(self):
        first_item = CartItem.objects.get(quantity=1)
        self.first.post(reverse('del_element_from_cart'), {'del_item': first_item.id})
        self.assertEqual(2, CartItem.objects.get().quantity)


class BonusCoinsPaymentTestCase(TestCase):
    def setUp(self):
        category = ProductCategory.objects.create(category='test')
        self.pizza = Product.objects.create(title='pizza', price=100, category=category)
        self.user = get_user_model().objects.create_user(username='test', password='test')
        self.client = Client()

    def checkout_with_bonus_coins(self):
        self.client.post(reverse('add_to_cart'), {'item_id': self.pizza.id})
        return self.client.post(reverse('checkout'), {**CHECKOUT_DATA, 'payment_choice': 'Bonus coins'})

    def test_not_enough_coins(self):
        self.user.bonus_coins = Decimal('99.99')
        self.user.save()
        self.client.login(username='test', password='test')

        response = self.checkout_with_bonus_coins()

        self.assertEqual(200, response.status_code)
        self.user.refresh_from_db()
        self.assertEqual(Decimal('99.99'), self.user.bonus_coins)
        self.assertFalse(Cart.objects.get().ordered)

    def test_anonymous_cannot_pay_with_coins(self):
        response = self.checkout_with_bonus_coins()
        self.assertEqual(200, response.status_code)
        self.assertFalse(Cart.objects.get().ordered)

    def test_enough_coins(self):
        self.user.bonus_coins = 150
        self.user.save()
        self.client.login(username='test', password='test')

        response = self.checkout_with_bonus_coins()

        self.assertEqual('/success/', response.url)
        self.user.refresh_from_db()
        self.assertEqual(Decimal('50'), self.user.bonus_coins)
        self.assertTrue(Cart.objects.get().ordered)


class CheckoutTwiceTestCase(TestCase):
    def setUp(self):
        category = ProductCategory.objects.create(category='test')
        self.pizza = Product.objects.create(title='pizza', price=100, category=category)
        get_user_model().objects.create_user(username='test', password='test')
        self.client = Client()
        self.client.login(username='test', password='test')
        self.client.post(reverse('add_to_cart'), {'item_id': self.pizza.id})

    def test_second_checkout_does_not_accrue_again(self):
        data = {**CHECKOUT_DATA, 'payment_choice': 'Cash'}
        self.client.post(reverse('checkout'), data)
        response = self.client.post(reverse('checkout'), data)

        self.assertEqual('/cart/', response.url)
        self.assertEqual(Decimal('1'), get_user_model().objects.get().bonus_coins)
        self.pizza.refresh_from_db()
        self.assertEqual(1, self.pizza.rating)


class StripeAmountTestCase(TestCase):
    def setUp(self):
        category = ProductCategory.objects.create(category='test')
        self.pizza = Product.objects.create(title='pizza', price=Decimal('10.55'), category=category)
        self.client = Client()

    @patch('stripe.Charge.create')
    def test_amount_keeps_kopecks(self, charge_create):
        for _ in range(3):
            self.client.post(reverse('add_to_cart'), {'item_id': self.pizza.id})
        self.client.post(reverse('create-charge'), {'stripeToken': 'tok_test'})
        self.assertEqual(3165, charge_create.call_args.kwargs['amount'])

    @patch('stripe.Charge.create')
    def test_charge_without_cart_does_nothing(self, charge_create):
        response = self.client.post(reverse('create-charge'), {'stripeToken': 'tok_test'})
        self.assertEqual('/cart/', response.url)
        charge_create.assert_not_called()
