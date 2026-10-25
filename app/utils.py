from decimal import Decimal, ROUND_DOWN

from django.contrib.auth import get_user_model
from django.db.models import F

from app.models import Cart, Product
import stripe


def get_session_key(request):
    if not request.session.session_key:
        request.session.save()
    return request.user.get_session_auth_hash() if request.user.is_authenticated else request.session.session_key


def cart_data(request):
    return Cart.objects.filter(session_key=get_session_key(request), ordered=False)


def stripe_card(request):
    cards = stripe.Customer.list_sources(
        request.user.stripe_customer_id,
        object='card'
    )
    return cards['data']


def stripe_amount(cart):
    return int(cart.get_total() * 100)


def accrual_bonus_coins(user, cart):
    if user.is_authenticated:
        bonus = (cart.get_total() * Decimal('0.01')).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
        get_user_model().objects.filter(pk=user.pk).update(bonus_coins=F('bonus_coins') + bonus)
        user.refresh_from_db(fields=['bonus_coins'])


def pay_with_bonus_coins(user, cart):
    if not user.is_authenticated:
        return False
    total = cart.get_total()
    paid = get_user_model().objects.filter(pk=user.pk, bonus_coins__gte=total).update(
        bonus_coins=F('bonus_coins') - total)
    user.refresh_from_db(fields=['bonus_coins'])
    return paid == 1


def save_cart_after_payment(cart):
    for cart_item in cart.items.all():
        cart_item.ordered = True
        cart_item.save(update_fields=['ordered'])
        Product.objects.filter(pk=cart_item.item_id).update(rating=F('rating') + 1)
    cart.ordered = True
    cart.save(update_fields=['ordered'])
