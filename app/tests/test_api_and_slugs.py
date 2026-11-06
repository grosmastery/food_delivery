from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from app.models import Cart, Product, ProductCategory

CHECKOUT_DATA = {
    'first_name': 'Анна-Марія',
    'last_name': "Мар'яненко",
    'address': 'test address',
    'phone_number': '0671234567',
    'payment_choice': 'Cash',
}


class CheckoutApiValidationTestCase(TestCase):
    def setUp(self):
        category = ProductCategory.objects.create(category='test')
        pizza = Product.objects.create(title='pizza', price=10, category=category)
        get_user_model().objects.create_user(username='test', password='test')
        self.client = APIClient()
        self.client.login(username='test', password='test')
        self.client.post(reverse('add_to_cart'), {'item_id': pizza.id})

    def test_valid_data(self):
        response = self.client.post('/api/checkout/', CHECKOUT_DATA)
        self.assertEqual(200, response.status_code, response.data)
        self.assertEqual('0671234567', Cart.objects.get().phone_number)

    def test_invalid_fields_rejected(self):
        for field, value in (
            ('phone_number', '067123456a'),
            ('phone_number', ''),
            ('first_name', 'Anna1'),
            ('last_name', '-Doe'),
        ):
            response = self.client.post('/api/checkout/', {**CHECKOUT_DATA, field: value})
            self.assertEqual(400, response.status_code, (field, value))
            self.assertIn(field, response.data)

    def test_missing_phone_rejected(self):
        data = {k: v for k, v in CHECKOUT_DATA.items() if k != 'phone_number'}
        response = self.client.post('/api/checkout/', data)
        self.assertEqual(400, response.status_code)
        self.assertIsNone(Cart.objects.get().phone_number)


class UniqueSlugTestCase(TestCase):
    def setUp(self):
        self.category = ProductCategory.objects.create(category='pizza')

    def product(self, title, category=None):
        return Product.objects.create(title=title, price=10, category=category or self.category)

    def test_same_titles_get_different_slugs(self):
        first, second, third = self.product('Margherita'), self.product('Margherita'), self.product('margherita')
        self.assertEqual(['margherita', 'margherita-2', 'margherita-3'], [first.slug, second.slug, third.slug])

    def test_resave_keeps_slug(self):
        self.product('Margherita')
        second = self.product('Margherita')
        second.save()
        self.assertEqual('margherita-2', second.slug)

    def test_non_latin_title_gets_fallback_slug(self):
        self.assertEqual(['product', 'product-2'], [self.product('Піца').slug, self.product('Борщ').slug])

    def test_detail_pages_for_duplicates(self):
        first, second = self.product('Margherita'), self.product('Margherita')
        for product in (first, second):
            response = Client().get(reverse('product_info', args=[self.category.slug, product.slug]))
            self.assertEqual(200, response.status_code)
            self.assertEqual(product, response.context_data['object'])

    def test_detail_page_with_wrong_category(self):
        product = self.product('Margherita')
        other = ProductCategory.objects.create(category='drinks')
        response = Client().get(reverse('product_info', args=[other.slug, product.slug]))
        self.assertEqual(404, response.status_code)

    def test_categories_and_users(self):
        self.assertEqual('pizza-2', ProductCategory.objects.create(category='Pizza').slug)
        first = get_user_model().objects.create_user(username='Ivan', password='test')
        second = get_user_model().objects.create_user(username='ivan', password='test')
        self.assertEqual(['ivan', 'ivan-2'], [first.slug, second.slug])
