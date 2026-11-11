from django.test import TestCase
from django.urls import reverse

from app.models import Product, ProductCategory


class SearchViewTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        pizza = ProductCategory.objects.create(category='Pizza')
        drinks = ProductCategory.objects.create(category='Drinks')
        cls.margherita = Product.objects.create(
            title='Margherita', compound='tomato, mozzarella, basil', price=10, category=pizza
        )
        cls.pepperoni = Product.objects.create(
            title='Pepperoni', compound='tomato, salami', price=12, category=pizza, rating=5
        )
        cls.mojito = Product.objects.create(title='Mojito', compound='lime, mint', price=5, category=drinks)

    def search(self, query, **extra):
        return self.client.get(reverse('search'), {'q': query, **extra})

    def test_empty_query_returns_no_results(self):
        response = self.search('')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['object_list']), [])

    def test_finds_by_title_case_insensitive(self):
        response = self.search('MOJ')
        self.assertEqual(list(response.context['object_list']), [self.mojito])

    def test_finds_by_compound(self):
        response = self.search('mozzarella')
        self.assertEqual(list(response.context['object_list']), [self.margherita])

    def test_finds_by_category_ordered_by_rating(self):
        response = self.search('pizza')
        self.assertEqual(list(response.context['object_list']), [self.pepperoni, self.margherita])

    def test_no_match_shows_empty_state(self):
        response = self.search('sushi')
        self.assertEqual(list(response.context['object_list']), [])
        self.assertContains(response, 'Nothing found')

    def test_query_is_escaped(self):
        response = self.search('<script>alert(1)</script>')
        self.assertNotContains(response, '<script>alert(1)</script>')

    def test_pagination_keeps_query(self):
        category = ProductCategory.objects.get(category='Pizza')
        for i in range(13):
            Product.objects.create(title=f'Pizza {i}', compound='dough', price=8, category=category)
        response = self.search('pizza')
        self.assertTrue(response.context['is_paginated'])
        self.assertContains(response, '?q=pizza&page=2')
        second = self.search('pizza', page=2)
        self.assertEqual(second.status_code, 200)

    def test_navbar_has_search_form(self):
        response = self.client.get('/')
        self.assertContains(response, 'action="/search/"')
