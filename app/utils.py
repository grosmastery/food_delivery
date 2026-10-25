from app.models import Cart
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


def accrual_bonus_coins(request):
    user = request.user
    if user.is_authenticated:
        user.bonus_coins += int(cart_data(request).first().get_total()) * 0.01
        user.save()


def save_cart_after_payment(request):
    cart = cart_data(request).first()
    for cart_item in cart.items.all():
        cart_item.ordered = True
        cart_item.item.rating += 1
        cart_item.item.save()
        cart_item.save()
    cart.ordered = True
    cart.save()
