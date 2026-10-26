from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from app.utils import merge_anonymous_cart


@receiver(user_logged_in)
def move_anonymous_cart_to_user(sender, request, user, **kwargs):
    if request is not None:
        merge_anonymous_cart(request, user)
