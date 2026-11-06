from django.contrib.auth import get_user_model
from rest_framework import serializers

from app.models import Cart, PaymentChoice, Product, ProductCategory
from app.validators import is_valid_name, is_valid_phone_number


class ProductCategorySerializer(serializers.Serializer):
    category = serializers.CharField()

    def save(self, **kwargs):
        return ProductCategory.objects.create(**self.validated_data)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        exclude = ('avatar', 'slug', 'groups', 'user_permissions', 'date_joined', 'last_login', 'password', 'is_active')
        read_only_fields = ('is_staff', 'is_superuser', 'bonus_coins', 'stripe_customer_id', 'default_card')


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        exclude = ('added',)


class CreateProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        exclude = ('added',)


class CheckoutSerializer(serializers.ModelSerializer):
    payment_choice = serializers.ChoiceField(choices=PaymentChoice.choices, required=True)

    class Meta:
        model = Cart
        fields = ('description', 'first_name', 'last_name', 'phone_number', 'address', 'payment_choice')
        extra_kwargs = {
            'phone_number': {'required': True, 'allow_null': False, 'allow_blank': False},
        }

    def validate_phone_number(self, value):
        if not is_valid_phone_number(value):
            raise serializers.ValidationError("Invalid phone number")
        return value

    def validate_first_name(self, value):
        if not is_valid_name(value):
            raise serializers.ValidationError("Invalid first name")
        return value

    def validate_last_name(self, value):
        if not is_valid_name(value):
            raise serializers.ValidationError("Invalid last name")
        return value

    def __init__(self, cart=None, *args, **kwargs):
        self.cart = cart
        super().__init__(*args, **kwargs)

    def save(self, commit=True, *args, **kwargs):
        cart = self.cart
        cart.update(**self.validated_data)
