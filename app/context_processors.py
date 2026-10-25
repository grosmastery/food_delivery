from app.models import ProductCategory, Cart
from app.utils import get_session_key, cart_data


def context_cart(request):
    cart = cart_data(request).first()
    return {"context_cart": cart}


def context_category(request):
    return {"context_category": ProductCategory.objects.all()}


def context_cart_exist(request):
    return {"context_cart_exist": Cart.objects.filter(session_key=get_session_key(request), ordered=False).exists()}
