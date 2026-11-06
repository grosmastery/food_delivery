from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.template.defaultfilters import slugify


def user_upload_to(obj, file_name):
    return f"users/{obj.username}/{file_name}"


def product_upload_to(obj, file_name):
    return f"products/{obj.category}/{file_name}"


def unique_slug(obj, value, fallback):
    base = slugify(value) or fallback
    slug = base
    number = 2
    others = type(obj).objects.exclude(pk=obj.pk)
    while others.filter(slug=slug).exists():
        slug = f'{base}-{number}'
        number += 1
    return slug


class UserProfile(AbstractUser):
    address = models.CharField(max_length=150, null=True, blank=True)
    phone_number = models.CharField(max_length=10)
    avatar = models.ImageField(upload_to=user_upload_to, null=True, blank=True)
    bonus_coins = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))
    slug = models.SlugField(unique=True)
    stripe_customer_id = models.CharField(max_length=250, null=True, blank=True)
    default_card = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        self.slug = unique_slug(self, self.username, 'user')
        super().save(*args, **kwargs)


class SameField(models.Model):
    main_image = models.ImageField(upload_to=product_upload_to, null=True, blank=True)
    slug = models.SlugField(null=True, unique=True)

    class Meta:
        abstract = True


class ProductCategory(SameField):
    category = models.CharField(max_length=50)

    def __str__(self):
        return self.category

    def save(self, *args, **kwargs):
        self.slug = unique_slug(self, self.category, 'category')
        super().save(*args, **kwargs)


class Product(SameField):
    title = models.CharField(max_length=50)
    compound = models.CharField(max_length=150)
    description = models.CharField(max_length=200)
    category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE)
    price = models.DecimalField(
        max_digits=8, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(250)]
    )
    available = models.BooleanField(default=True)
    rating = models.IntegerField(default=0)
    added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.slug = unique_slug(self, self.title, 'product')
        super().save(*args, **kwargs)


class Image(models.Model):
    product = models.ForeignKey('app.Product', on_delete=models.CASCADE)
    images = models.ImageField(upload_to='products/images/', null=True, blank=True)

    def __str__(self):
        return self.product.title


class CartItem(models.Model):
    cart = models.ForeignKey('app.Cart', on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['cart', 'item'], name='unique_cart_item'),
        ]

    def __str__(self):
        return f'{self.item} || {self.quantity}'

    def get_total_price(self):
        return self.quantity * self.item.price


class PaymentChoice(models.TextChoices):
    CARD = 'Card', 'Card'
    CASH = 'Cash', 'Cash'
    BONUS_COINS = 'Bonus coins', 'Bonus coins'


class Cart(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, null=True, blank=True)
    ordered_date = models.DateTimeField(auto_now_add=True)
    ordered = models.BooleanField(default=False)
    session_key = models.CharField(max_length=255, editable=False)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    address = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=10, null=True, blank=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    payment_choice = models.CharField(max_length=40, choices=PaymentChoice.choices)
    stripe_payment_intent_id = models.CharField(max_length=255, null=True, blank=True, editable=False)

    def __str__(self):
        return f'{self.user} || {self.ordered}'

    def get_total(self):
        return sum((item.get_total_price() for item in self.items.all()), Decimal('0'))

    def items_counter(self):
        return sum(item.quantity for item in self.items.all())


class Room(models.Model):
    room_name = models.CharField(max_length=255)

    def __str__(self):
        return self.room_name


class Messages(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    from_user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    message = models.TextField()

    def __str__(self):
        return self.from_user.username
