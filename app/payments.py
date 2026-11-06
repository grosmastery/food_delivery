import logging

import stripe
from django.conf import settings

from app.utils import stripe_amount

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY

CURRENCY = 'uah'
EDITABLE_STATUSES = ('requires_payment_method', 'requires_confirmation', 'requires_action')
AUTOMATIC_PAYMENT_METHODS = {'enabled': True, 'allow_redirects': 'never'}


def saved_card(user):
    if not (user.is_authenticated and user.stripe_customer_id):
        return None
    try:
        methods = stripe.Customer.list_payment_methods(user.stripe_customer_id, type='card', limit=1)
    except stripe.StripeError:
        logger.exception('Could not load saved card')
        return None
    if not methods.data:
        return None
    method = methods.data[0]
    return {
        'id': method.id,
        'last4': method.card.last4,
        'exp_month': method.card.exp_month,
        'exp_year': method.card.exp_year,
    }


def get_or_create_customer(user):
    if not user.stripe_customer_id:
        customer = stripe.Customer.create(email=user.email, name=f'{user.first_name} {user.last_name}'.strip())
        user.stripe_customer_id = customer.id
        user.save(update_fields=['stripe_customer_id'])
    return user.stripe_customer_id


def prepare_payment_intent(cart, user):
    amount = stripe_amount(cart)
    if cart.stripe_payment_intent_id:
        intent = stripe.PaymentIntent.retrieve(cart.stripe_payment_intent_id)
        if intent.status in EDITABLE_STATUSES and intent.amount != amount:
            intent = stripe.PaymentIntent.modify(intent.id, amount=amount)
        return intent

    params = {
        'amount': amount,
        'currency': CURRENCY,
        'automatic_payment_methods': AUTOMATIC_PAYMENT_METHODS,
        'description': f'Order #{cart.id}',
        'metadata': {'cart_id': cart.id},
    }
    if user.is_authenticated and user.stripe_customer_id:
        params['customer'] = user.stripe_customer_id
    intent = stripe.PaymentIntent.create(**params)
    cart.stripe_payment_intent_id = intent.id
    cart.save(update_fields=['stripe_payment_intent_id'])
    return intent


def confirm_payment_intent(intent, payment_method):
    if intent.status == 'succeeded':
        return intent
    return stripe.PaymentIntent.confirm(intent.id, payment_method=payment_method)


def needs_authentication(intent):
    return intent.status == 'requires_action' and intent.next_action and intent.next_action.type == 'use_stripe_sdk'


def is_paid(intent, cart):
    return (
        intent.status == 'succeeded'
        and intent.amount == stripe_amount(cart)
        and intent.currency == CURRENCY
        and intent.metadata['cart_id'] == str(cart.id)
    )
