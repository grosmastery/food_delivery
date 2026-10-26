from app.models import ProductCategory
from app.utils import cart_data


def context_cart(request):
    cart = cart_data(request).first()
    return {"context_cart": cart}


def context_category(request):
    return {"context_category": ProductCategory.objects.all()}


def context_cart_exist(request):
    return {"context_cart_exist": cart_data(request).exists()}
