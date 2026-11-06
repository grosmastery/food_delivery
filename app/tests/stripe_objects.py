import stripe

from app.utils import stripe_amount


def payment_intent(cart, status='succeeded', amount=None, next_action=None, intent_id='pi_test'):
    return stripe.PaymentIntent.construct_from(
        {
            'id': intent_id,
            'object': 'payment_intent',
            'status': status,
            'amount': stripe_amount(cart) if amount is None else amount,
            'currency': 'uah',
            'metadata': {'cart_id': str(cart.id)},
            'client_secret': f'{intent_id}_secret',
            'next_action': next_action,
        },
        'sk_test',
    )


def card_list(*method_ids):
    return stripe.ListObject.construct_from(
        {
            'object': 'list',
            'url': '/v1/customers/cus_test/payment_methods',
            'has_more': False,
            'data': [
                {
                    'id': method_id,
                    'object': 'payment_method',
                    'card': {'last4': '4242', 'exp_month': 12, 'exp_year': 2030},
                }
                for method_id in method_ids
            ],
        },
        'sk_test',
    )


def setup_intent(status='succeeded', customer='cus_test', payment_method='pm_new'):
    return stripe.SetupIntent.construct_from(
        {
            'id': 'seti_test',
            'object': 'setup_intent',
            'status': status,
            'customer': customer,
            'payment_method': payment_method,
            'client_secret': 'seti_test_secret',
        },
        'sk_test',
    )
