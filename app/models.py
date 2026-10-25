from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.template.defaultfilters import slugify


def user_upload_to(obj, file_name):
    return f"users/{obj.username}/{file_name}"


def product_upload_to(obj, file_name):
    return f"products/{obj.category}/{file_name}"


class UserProfile(AbstractUser):
    address = models.CharField(max_length=150, null=True, blank=True)
    phone_number = models.CharField(max_length=10)
    avatar = models.ImageField(upload_to=user_upload_to, null=True, blank=True)
    bonus_coins = models.FloatField(default=0)
    order_history = models.ManyToManyField("app.Cart")
    slug = models.SlugField()
    stripe_customer_id = models.CharField(max_length=250, null=True, blank=True)
    default_card = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        self.slug = slugify(self.username)
        super(get_user_model(), self).save(*args, **kwargs)


class SameField(models.Model):
    main_image = models.ImageField(upload_to=product_upload_to, null=True, blank=True)
    slug = models.SlugField(null=True)

    class Meta:
        abstract = True


class ProductCategory(SameField):
    category = models.CharField(max_length=50)

    def __str__(self):
        return self.category

    def save(self, *args, **kwargs):
        self.slug = slugify(self.category)
        super(ProductCategory, self).save(*args, **kwargs)


class Product(SameField):
    title = models.CharField(max_length=50)
    compound = models.CharField(max_length=150)
    description = models.CharField(max_length=200)
    category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE)
    price = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(250)])
    available = models.BooleanField(default=True)
    rating = models.IntegerField(default=0)
    added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)
        super(Product, self).save(*args, **kwargs)


class Image(models.Model):
    product = models.ForeignKey('app.Product', on_delete=models.CASCADE)
    images = models.ImageField(upload_to='products/images/', null=True, blank=True)

    def __str__(self):
        return self.product.title


class CartItem(models.Model):
    ordered = models.BooleanField(default=False)
    item = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

    def __str__(self):
        return f'{self.item} || {self.quantity}'

    def get_total_price(self):
        return self.quantity * self.item.price


class Cart(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, null=True, blank=True)
    items = models.ManyToManyField(CartItem)
    ordered_date = models.DateTimeField(auto_now_add=True)
    ordered = models.BooleanField(default=False)
    session_key = models.CharField(max_length=255, editable=False)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    address = models.CharField(max_length=150)
    phone_number = models.IntegerField(null=True, blank=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    payment_choice = models.CharField(max_length=40)

    def __str__(self):
        return f'{self.user} || {self.ordered}'

    def get_total(self):
        return list(map(lambda e, i: e + i.get_total_price(), [0], self.items.all()))[0]

    def items_counter(self):  # todo  для глбального отображение кол-ва предметов в корзине, нужно ли?
        total = 0
        for item in self.items.all():
            total += item.quantity
        return list(map(lambda k, i: k + i.quantity, [0], self.items.all()))[0]


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
