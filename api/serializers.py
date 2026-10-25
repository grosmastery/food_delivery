from abc import ABC

from django.contrib.auth import get_user_model
from rest_framework import serializers

from app.models import ProductCategory, Product, Cart


class ProductCategorySerializer(serializers.Serializer):
    category = serializers.CharField()

    def save(self, **kwargs):
        return ProductCategory.objects.create(**self.validated_data)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        exclude = (
            'avatar', 'slug', 'order_history', 'groups', 'user_permissions', 'date_joined', 'last_login', 'password',
            'is_active')


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        exclude = ('added',)


class CreateProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        exclude = ('added',)


class CheckoutSerializer(serializers.ModelSerializer):
    CHOICES = (
        ('Card', 'Card'),
        ('Cash', 'Cash'),
        ('Bonus coins', 'Bonus coins')
    )

    payment_choice = serializers.ChoiceField(choices=CHOICES, required=True)

    class Meta:
        model = Cart
        fields = ('description', 'first_name', 'last_name', 'phone_number', 'address', 'payment_choice')

    def __init__(self, cart=None, *args, **kwargs):
        self.cart = cart
        super(CheckoutSerializer, self).__init__(*args, **kwargs)

    def save(self, commit=True, *args, **kwargs):
        cart = self.cart
        cart.update(**self.validated_data)
