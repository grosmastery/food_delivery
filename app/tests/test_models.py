from django.test import TestCase
from django.contrib.auth import get_user_model
from app.models import UserProfile, ProductCategory, Product, Image, CartItem, Cart


class UserProfileTestCase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='testuser',
            password='secret',
            address='Test Address',
            phone_number='1234567890'
        )

    def test_user_profile_created(self):
        user_profile = get_user_model().objects.get(username=self.user)
        self.assertEqual(user_profile.address, 'Test Address')
        self.assertEqual(user_profile.phone_number, '1234567890')


class ProductCategoryTestCase(TestCase):
    def setUp(self):
        self.product_category = ProductCategory.objects.create(
            category='Test Category'
        )

    def test_product_category_created(self):
        product_category = ProductCategory.objects.get(category='Test Category')
        self.assertEqual(product_category.category, 'Test Category')


class ProductTestCase(TestCase):
    def setUp(self):
        self.product_category = ProductCategory.objects.create(
            category='Test Category'
        )
        self.product = Product.objects.create(
            title='Test Product',
            compound='Test Compound',
            description='Test Description',
            category=self.product_category,
            price=100.0
        )

    def test_product_created(self):
        product = Product.objects.get(title='Test Product')
        self.assertEqual(product.compound, 'Test Compound')
        self.assertEqual(product.description, 'Test Description')
        self.assertEqual(product.category, self.product_category)
        self.assertEqual(product.price, 100.0)


class ImageTestCase(TestCase):
    def setUp(self):
        self.product_category = ProductCategory.objects.create(
            category='Test Category'
        )
        self.product = Product.objects.create(
            title='Test Product',
            compound='Test Compound',
            description='Test Description',
            category=self.product_category,
            price=100.0
        )
        self.image = Image.objects.create(
            product=self.product
        )

    def test_image_created(self):
        image = Image.objects.get(product=self.product)
        self.assertEqual(image.product, self.product)


class CartItemModelTestCase(TestCase):

    def setUp(self):
        self.product = Product.objects.create(
            name='Test Product',
            price=10.0
        )
        self.cart_item = CartItem.objects.create(
            item=self.product,
            quantity=2
        )

    def test_get_total_price(self):
        total = self.cart_item.get_total_price()
        self.assertEqual(total, 20.0)

    def test_str_representation(self):
        self.assertEqual(str(self.cart_item), 'Test Product || 2')


class CartModelTestCase(TestCase):
    def setUp(self):
        # Create some test data
        User = get_user_model()
        self.user = User.objects.create_user(
            username='testuser', password='secret'
        )
        self.product1 = Product.objects.create(
            name='Test Product 1', price=10.0
        )
        self.product2 = Product.objects.create(
            name='Test Product 2', price=20.0
        )
        self.cartitem1 = CartItem.objects.create(
            item=self.product1, quantity=2
        )
        self.cartitem2 = CartItem.objects.create(
            item=self.product2, quantity=3
        )
        self.cart = Cart.objects.create(
            user=self.user, first_name='John', last_name='Doe',
            address='123 Main St', phone_number='555-555-5555',
            payment_choice='Credit Card'
        )
        self.cart.items.add(self.cartitem1, self.cartitem2)

    def test_cart_get_total(self):
        # Test that the get_total method returns the correct total
        total = self.cart.get_total()
        self.assertEqual(total, 90.0)

    def test_cart_str(self):
        # Test the string representation of the Cart model
        self.assertEqual(str(self.cart), 'testuser || False')

    def test_cartitem_str(self):
        # Test the string representation of the CartItem model
        self.assertEqual(str(self.cartitem1), 'Test Product 1 || 2')

    def test_cartitem_get_total_price(self):
        # Test the get_total_price method of the CartItem model
        total_price = self.cartitem1.get_total_price()
        self.assertEqual(total_price, 20.0)
