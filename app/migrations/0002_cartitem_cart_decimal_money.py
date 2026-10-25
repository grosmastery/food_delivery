from decimal import Decimal

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


def move_items_to_carts(apps, schema_editor):
    Cart = apps.get_model('app', 'Cart')
    CartItem = apps.get_model('app', 'CartItem')

    for cart in Cart.objects.all():
        copies = {}
        for cart_item in cart.items.all():
            copy = copies.get(cart_item.item_id)
            if copy:
                copy.quantity += cart_item.quantity
                copy.save()
            else:
                copies[cart_item.item_id] = CartItem.objects.create(
                    new_cart=cart,
                    item_id=cart_item.item_id,
                    quantity=cart_item.quantity,
                    ordered=cart.ordered,
                )

    CartItem.objects.filter(new_cart__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='cartitem',
            name='new_cart',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+',
                                    to='app.cart'),
        ),
        migrations.RunPython(move_items_to_carts, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='cart',
            name='items',
        ),
        migrations.RenameField(
            model_name='cartitem',
            old_name='new_cart',
            new_name='cart',
        ),
        migrations.AlterField(
            model_name='cartitem',
            name='cart',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items',
                                    to='app.cart'),
        ),
        migrations.AddConstraint(
            model_name='cartitem',
            constraint=models.UniqueConstraint(fields=('cart', 'item'), name='unique_cart_item'),
        ),
        migrations.AlterField(
            model_name='product',
            name='price',
            field=models.DecimalField(decimal_places=2, max_digits=8,
                                      validators=[django.core.validators.MinValueValidator(0),
                                                  django.core.validators.MaxValueValidator(250)]),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='bonus_coins',
            field=models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10),
        ),
    ]
