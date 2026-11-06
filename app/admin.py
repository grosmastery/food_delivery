from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from app.models import Cart, CartItem, Image, Messages, Product, ProductCategory, Room, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(UserAdmin):
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            _("Personal info"),
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "email",
                    "address",
                    "avatar",
                    "phone_number",
                    "stripe_customer_id",
                    "default_card",
                )
            },
        ),
        (_("User bonus coins"), {"fields": ("bonus_coins",)}),
        (_("Permissions"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    class Meta:
        model = get_user_model()


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    fieldsets = ((None, {"fields": ("category", "main_image")}),)


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'ordered')
    readonly_fields = ('session_key',)
    inlines = [CartItemInline]


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('item', 'quantity', 'cart')


class ImageAdmin(admin.StackedInline):
    model = Image


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'rating', 'available')
    fieldsets = (
        (
            None,
            {"fields": ("title", "compound", "description", "price", "category", "main_image", "rating", "available")},
        ),
    )

    readonly_fields = ('added',)

    inlines = [ImageAdmin]

    class Meta:
        model = Product


@admin.register(Image)
class ProductImageAdmin(admin.ModelAdmin):
    pass


@admin.register(Messages)
class MessageAdmin(admin.ModelAdmin):
    pass


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    pass
