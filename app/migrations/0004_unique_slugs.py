from django.db import migrations, models
from django.template.defaultfilters import slugify


def make_slugs_unique(apps, schema_editor):
    for model_name, source_field, fallback in (
            ('Product', 'title', 'product'),
            ('ProductCategory', 'category', 'category'),
            ('UserProfile', 'username', 'user'),
    ):
        model = apps.get_model('app', model_name)
        used = set()
        for obj in model.objects.order_by('pk'):
            base = slugify(getattr(obj, source_field)) or fallback
            slug = base
            number = 2
            while slug in used:
                slug = f'{base}-{number}'
                number += 1
            used.add(slug)
            if obj.slug != slug:
                model.objects.filter(pk=obj.pk).update(slug=slug)


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0003_cart_phone_number_char'),
    ]

    operations = [
        migrations.RunPython(make_slugs_unique, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='product',
            name='slug',
            field=models.SlugField(null=True, unique=True),
        ),
        migrations.AlterField(
            model_name='productcategory',
            name='slug',
            field=models.SlugField(null=True, unique=True),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='slug',
            field=models.SlugField(unique=True),
        ),
    ]
