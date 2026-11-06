from decimal import Decimal
from unittest.mock import patch

import stripe
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from app.models import Cart, Product, ProductCategory
from app.tests.stripe_objects import card_list, payment_intent, setup_intent

SDK_ACTION = {'type': 'use_stripe_sdk', 'use_stripe_sdk': {}}


class PaymentTestCase(TestCase):
    def setUp(self):
        category = ProductCategory.objects.create(category='test')
        self.pizza = Product.objects.create(title='pizza', price=Decimal('10.55'), category=category)
        self.user = get_user_model().objects.create_user(username='test', password='test')
        self.client = Client()

    def login(self, **fields):
        for name, value in fields.items():
            setattr(self.user, name, value)
        self.user.save()
        self.client.login(username='test', password='test')

    def add_pizza(self, times=1):
        for _ in range(times):
            self.client.post(reverse('add_to_cart'), {'item_id': self.pizza.id})
        return Cart.objects.get(ordered=False)

    def pay(self, **data):
        return self.client.post(reverse('create-charge'), data or {'payment_method_id': 'pm_card_visa'})

    def confirm(self):
        return self.client.post(reverse('confirm-charge'))


class NewCardPaymentTestCase(PaymentTestCase):
    @patch('stripe.PaymentIntent.confirm')
    @patch('stripe.PaymentIntent.create')
    def test_payment_succeeds(self, intent_create, intent_confirm):
        self.login()
        cart = self.add_pizza(times=3)
        intent_create.return_value = payment_intent(cart, status='requires_payment_method')
        intent_confirm.return_value = payment_intent(cart)

        response = self.pay()

        self.assertEqual({'redirect': '/success/'}, response.json())
        create_params = intent_create.call_args.kwargs
        self.assertEqual(3165, create_params['amount'])
        self.assertEqual('uah', create_params['currency'])
        self.assertEqual({'enabled': True, 'allow_redirects': 'never'}, create_params['automatic_payment_methods'])
        self.assertEqual({'cart_id': cart.id}, create_params['metadata'])
        intent_confirm.assert_called_once_with('pi_test', payment_method='pm_card_visa')
        cart.refresh_from_db()
        self.assertTrue(cart.ordered)
        self.assertEqual('pi_test', cart.stripe_payment_intent_id)
        self.user.refresh_from_db()
        self.assertEqual(Decimal('0.31'), self.user.bonus_coins)

    @patch('stripe.PaymentIntent.retrieve')
    @patch('stripe.PaymentIntent.confirm')
    @patch('stripe.PaymentIntent.create')
    def test_3d_secure_flow(self, intent_create, intent_confirm, intent_retrieve):
        cart = self.add_pizza()
        intent_create.return_value = payment_intent(cart, status='requires_payment_method')
        intent_confirm.return_value = payment_intent(cart, status='requires_action', next_action=SDK_ACTION)

        response = self.pay()

        self.assertEqual({'requires_action': True, 'client_secret': 'pi_test_secret'}, response.json())
        self.assertFalse(Cart.objects.get().ordered)

        intent_retrieve.return_value = payment_intent(cart)

        response = self.confirm()

        self.assertEqual({'redirect': '/success/'}, response.json())
        intent_retrieve.assert_called_once_with('pi_test')
        intent_confirm.assert_called_once()
        self.assertTrue(Cart.objects.get().ordered)

    @patch('stripe.PaymentIntent.retrieve')
    @patch('stripe.PaymentIntent.confirm')
    @patch('stripe.PaymentIntent.create')
    def test_3d_secure_not_completed(self, intent_create, intent_confirm, intent_retrieve):
        cart = self.add_pizza()
        intent_create.return_value = payment_intent(cart, status='requires_payment_method')
        intent_confirm.return_value = payment_intent(cart, status='requires_action', next_action=SDK_ACTION)
        self.pay()
        intent_retrieve.return_value = payment_intent(cart, status='requires_action', next_action=SDK_ACTION)

        response = self.confirm()

        self.assertEqual(402, response.status_code)
        self.assertFalse(Cart.objects.get().ordered)

    @patch('stripe.PaymentIntent.create')
    def test_amount_too_small(self, intent_create):
        self.add_pizza()
        intent_create.side_effect = stripe.InvalidRequestError(
            'Amount must convert to at least 30 pence.', 'amount', code='amount_too_small'
        )

        response = self.pay()

        self.assertEqual(400, response.status_code)
        self.assertIn('too small', response.json()['error'])

    @patch('stripe.PaymentIntent.confirm')
    @patch('stripe.PaymentIntent.create')
    def test_card_declined(self, intent_create, intent_confirm):
        cart = self.add_pizza()
        intent_create.return_value = payment_intent(cart, status='requires_payment_method')
        intent_confirm.side_effect = stripe.CardError(
            'Your card was declined.',
            None,
            'card_declined',
            json_body={'error': {'message': 'Your card was declined.'}},
        )

        response = self.pay()

        self.assertEqual(402, response.status_code)
        self.assertEqual('Your card was declined.', response.json()['error'])
        self.assertFalse(Cart.objects.get().ordered)

    @patch('stripe.PaymentIntent.modify')
    @patch('stripe.PaymentIntent.retrieve')
    @patch('stripe.PaymentIntent.confirm')
    @patch('stripe.PaymentIntent.create')
    def test_retry_reuses_intent_and_updates_amount(
        self, intent_create, intent_confirm, intent_retrieve, intent_modify
    ):
        cart = self.add_pizza()
        intent_create.return_value = payment_intent(cart, status='requires_payment_method')
        intent_confirm.return_value = payment_intent(cart, status='requires_payment_method')
        self.assertEqual(402, self.pay().status_code)

        cart = self.add_pizza()
        intent_retrieve.return_value = payment_intent(cart, status='requires_payment_method', amount=1055)
        intent_modify.return_value = payment_intent(cart, status='requires_payment_method')
        intent_confirm.return_value = payment_intent(cart)

        response = self.pay(payment_method_id='pm_other')

        self.assertEqual({'redirect': '/success/'}, response.json())
        intent_create.assert_called_once()
        intent_modify.assert_called_once_with('pi_test', amount=2110)
        intent_confirm.assert_called_with('pi_test', payment_method='pm_other')

    @patch('stripe.PaymentIntent.confirm')
    @patch('stripe.PaymentIntent.create')
    def test_paid_amount_must_match_cart(self, intent_create, intent_confirm):
        cart = self.add_pizza()
        intent_create.return_value = payment_intent(cart, status='requires_payment_method')
        intent_confirm.return_value = payment_intent(cart, amount=100)

        response = self.pay()

        self.assertEqual(409, response.status_code)
        self.assertFalse(Cart.objects.get().ordered)

    @patch('stripe.PaymentIntent.create')
    def test_payment_method_required(self, intent_create):
        self.add_pizza()
        response = self.pay(payment_method_id='')
        self.assertEqual(400, response.status_code)
        intent_create.assert_not_called()

    def test_confirm_without_intent(self):
        self.add_pizza()
        self.assertEqual(400, self.confirm().status_code)

    @patch('stripe.PaymentIntent.create')
    def test_without_cart(self, intent_create):
        self.assertEqual('/cart/', self.client.get(reverse('create-charge')).url)
        self.assertEqual({'redirect': '/cart/'}, self.pay().json())
        self.assertEqual({'redirect': '/cart/'}, self.confirm().json())
        intent_create.assert_not_called()


class SavedCardPaymentTestCase(PaymentTestCase):
    @patch('stripe.Customer.list_payment_methods', return_value=card_list('pm_saved'))
    def test_payment_page_shows_saved_card(self, list_methods):
        self.login(stripe_customer_id='cus_test', default_card=True)
        self.add_pizza()
        response = self.client.get(reverse('create-charge'))
        self.assertEqual('4242', response.context['card']['last4'])

    @patch('stripe.Customer.list_payment_methods', return_value=card_list('pm_saved'))
    @patch('stripe.PaymentIntent.confirm')
    @patch('stripe.PaymentIntent.create')
    def test_pay_with_saved_card(self, intent_create, intent_confirm, list_methods):
        self.login(stripe_customer_id='cus_test', default_card=True)
        cart = self.add_pizza()
        intent_create.return_value = payment_intent(cart, status='requires_payment_method')
        intent_confirm.return_value = payment_intent(cart)

        response = self.pay(use_default='true')

        self.assertEqual({'redirect': '/success/'}, response.json())
        self.assertEqual('cus_test', intent_create.call_args.kwargs['customer'])
        intent_confirm.assert_called_once_with('pi_test', payment_method='pm_saved')

    @patch('stripe.Customer.list_payment_methods', return_value=card_list())
    @patch('stripe.PaymentIntent.create')
    def test_saved_card_missing(self, intent_create, list_methods):
        self.login(stripe_customer_id='cus_test', default_card=True)
        self.add_pizza()
        self.assertEqual(400, self.pay(use_default='true').status_code)
        intent_create.assert_not_called()

    @patch('stripe.Customer.list_payment_methods', return_value=card_list('pm_saved'))
    def test_profile_shows_saved_card(self, list_methods):
        self.login(stripe_customer_id='cus_test', default_card=True)
        response = self.client.get(f'/{self.user.slug}/profile/')
        self.assertEqual('4242', response.context['object']['last4'])


class SaveCardTestCase(PaymentTestCase):
    @patch('stripe.Customer.list_payment_methods', return_value=card_list())
    @patch('stripe.SetupIntent.create', return_value=setup_intent(status='requires_payment_method'))
    @patch('stripe.Customer.create')
    def test_card_page_creates_customer_and_setup_intent(self, customer_create, setup_create, list_methods):
        customer_create.return_value = stripe.Customer.construct_from({'id': 'cus_new'}, 'sk_test')
        self.login(email='test@test.com', first_name='Test')

        response = self.client.get(reverse('update_card'))

        self.assertEqual('seti_test_secret', response.context['client_secret'])
        self.assertEqual('cus_new', setup_create.call_args.kwargs['customer'])
        self.assertEqual('never', setup_create.call_args.kwargs['automatic_payment_methods']['allow_redirects'])
        self.user.refresh_from_db()
        self.assertEqual('cus_new', self.user.stripe_customer_id)

    @patch('stripe.SetupIntent.create')
    @patch('stripe.Customer.create')
    def test_card_page_reuses_customer(self, customer_create, setup_create):
        setup_create.return_value = setup_intent(status='requires_payment_method')
        self.login(stripe_customer_id='cus_test')
        with patch('stripe.Customer.list_payment_methods', return_value=card_list()):
            self.client.get(reverse('update_card'))
        customer_create.assert_not_called()

    @patch('stripe.SetupIntent.create', side_effect=stripe.APIConnectionError('down'))
    @patch('stripe.Customer.create', side_effect=stripe.APIConnectionError('down'))
    def test_card_page_when_stripe_is_down(self, customer_create, setup_create):
        self.login()
        response = self.client.get(reverse('update_card'))
        self.assertEqual(f'/{self.user.slug}/profile/', response.url)

    @patch('stripe.PaymentMethod.detach')
    @patch('stripe.Customer.list_payment_methods', return_value=card_list('pm_old', 'pm_new'))
    @patch('stripe.SetupIntent.retrieve', return_value=setup_intent())
    def test_save_card_replaces_old_one(self, setup_retrieve, list_methods, detach):
        self.login(stripe_customer_id='cus_test')

        response = self.client.post(reverse('update_card'), {'setup_intent_id': 'seti_test'})

        self.assertEqual(f'/{self.user.slug}/profile/', response.url)
        detach.assert_called_once_with('pm_old')
        self.user.refresh_from_db()
        self.assertTrue(self.user.default_card)

    @patch('stripe.PaymentMethod.detach')
    @patch('stripe.SetupIntent.retrieve', return_value=setup_intent(customer='cus_other'))
    def test_cannot_save_foreign_setup_intent(self, setup_retrieve, detach):
        self.login(stripe_customer_id='cus_test')

        response = self.client.post(reverse('update_card'), {'setup_intent_id': 'seti_test'})

        self.assertEqual(reverse('update_card'), response.url)
        detach.assert_not_called()
        self.user.refresh_from_db()
        self.assertFalse(self.user.default_card)
