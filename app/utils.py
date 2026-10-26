from decimal import Decimal, ROUND_DOWN

from django.contrib.auth import get_user_model
from django.db.models import F

from app.models import Cart, CartItem, Product
import stripe


def get_session_key(request):
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key


def cart_data(request):
    carts = Cart.objects.filter(ordered=False)
    if request.user.is_authenticated:
        return carts.filter(user=request.user)
    return carts.filter(session_key=get_session_key(request), user__isnull=True)


def merge_anonymous_cart(request, user):
    cart_id = request.session.pop('cart_id', None)
    anonymous_cart = Cart.objects.filter(id=cart_id, user__isnull=True, ordered=False).first()
    if anonymous_cart is None:
        return

    user_cart = Cart.objects.filter(user=user, ordered=False).first()
    if user_cart is None:
        anonymous_cart.user = user
        anonymous_cart.save(update_fields=['user'])
        return

    for cart_item in anonymous_cart.items.all():
        user_item, created = CartItem.objects.get_or_create(
            cart=user_cart, item_id=cart_item.item_id, defaults={'quantity': cart_item.quantity})
        if not created:
            user_item.quantity = F('quantity') + cart_item.quantity
            user_item.save(update_fields=['quantity'])
    anonymous_cart.delete()


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
