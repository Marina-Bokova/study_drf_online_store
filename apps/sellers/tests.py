from decimal import Decimal
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.profiles.models import Order, OrderItem, ShippingAddress
from apps.sellers.models import Seller
from apps.shop.models import Category, Product


class SellersBaseTestCase(TestCase):
    @staticmethod
    def make_test_image(name="test.png"):
        buffer = BytesIO()
        Image.new("RGB", (1, 1), "white").save(buffer, format="PNG")
        return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            first_name="Buyer",
            last_name="User",
            email="buyer@example.com",
            password="StrongPass123",
        )
        cls.other_user = User.objects.create_user(
            first_name="Other",
            last_name="Seller",
            email="other@example.com",
            password="StrongPass123",
            account_type="SELLER",
        )
        cls.approved_seller = Seller.objects.create(
            user=cls.other_user,
            business_name="Existing Store",
            inn_identification_number="1234567890",
            phone_number="1234567890",
            business_address="Main street 1",
            city="Tomsk",
            postal_code="634000",
            bank_name="Test Bank",
            bank_bic_number="123456789",
            bank_current_account="12345678901234567890",
            bank_correspondent_account="12345678901234567890",
            is_approved=True,
        )
        cls.category = Category.objects.create(
            name="Phones",
            image=cls.make_test_image("category.png"),
        )
        cls.product = Product.objects.create(
            seller=cls.approved_seller,
            name="Phone X",
            desc="Flagship phone",
            price_current=Decimal("99.99"),
            category=cls.category,
            in_stock=5,
            image1=cls.make_test_image("product.png"),
        )

    def setUp(self):
        self.client = APIClient()

    def get_seller_payload(self, **overrides):
        payload = {
            "business_name": "Marina Shop",
            "inn_identification_number": "9876543210",
            "website_url": "https://example.com",
            "phone_number": "9998887766",
            "business_description": "Electronics store",
            "business_address": "Lenina 1",
            "city": "Tomsk",
            "postal_code": "634050",
            "bank_name": "Sample Bank",
            "bank_bic_number": "987654321",
            "bank_current_account": "11112222333344445555",
            "bank_correspondent_account": "55554444333322221111",
        }
        payload.update(overrides)
        return payload

    def get_product_payload(self, **overrides):
        payload = {
            "name": "Phone Pro",
            "desc": "Updated flagship phone",
            "price_current": "149.99",
            "category_slug": self.category.slug,
            "in_stock": 3,
            "image1": self.make_test_image("phone.png"),
        }
        payload.update(overrides)
        return payload


class SellersViewTests(SellersBaseTestCase):
    def test_post_creates_seller_and_switches_user_to_seller_role(self):
        self.client.force_authenticate(self.user)

        response = self.client.post("/sellers/", self.get_seller_payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.user.refresh_from_db()
        seller = Seller.objects.get(user=self.user)
        self.assertEqual(self.user.account_type, "SELLER")
        self.assertEqual(seller.business_name, "Marina Shop")
        self.assertFalse(seller.is_approved)
        self.assertEqual(response.data["business_name"], "Marina Shop")

    def test_post_updates_existing_seller_profile_for_same_user(self):
        seller = Seller.objects.create(
            user=self.user,
            business_name="Old Name",
            inn_identification_number="1111111111",
            phone_number="1111111111",
            business_address="Old address",
            city="Tomsk",
            postal_code="634000",
            bank_name="Old Bank",
            bank_bic_number="123123123",
            bank_current_account="11111111111111111111",
            bank_correspondent_account="22222222222222222222",
        )
        self.client.force_authenticate(self.user)

        response = self.client.post(
            "/sellers/",
            self.get_seller_payload(business_name="New Name"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        seller.refresh_from_db()
        self.assertEqual(Seller.objects.filter(user=self.user).count(), 1)
        self.assertEqual(seller.business_name, "New Name")


class SellerProductsViewTests(SellersBaseTestCase):
    def test_get_returns_products_for_approved_seller(self):
        self.client.force_authenticate(self.other_user)

        response = self.client.get("/sellers/products/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], self.product.name)

    def test_get_returns_403_for_user_without_approved_seller_profile(self):
        self.client.force_authenticate(self.user)

        response = self.client.get("/sellers/products/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_post_creates_product_for_approved_seller(self):
        self.client.force_authenticate(self.other_user)

        response = self.client.post(
            "/sellers/products/",
            self.get_product_payload(),
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Product.objects.filter(name="Phone Pro", seller=self.approved_seller).exists())

    def test_post_returns_404_for_missing_category(self):
        self.client.force_authenticate(self.other_user)

        response = self.client.post(
            "/sellers/products/",
            self.get_product_payload(category_slug="missing-category"),
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class SellerProductViewTests(SellersBaseTestCase):
    def test_put_updates_product_and_moves_current_price_to_old_price(self):
        self.client.force_authenticate(self.other_user)

        response = self.client.put(
            f"/sellers/products/{self.product.slug}/",
            self.get_product_payload(
                name=self.product.name,
                price_current="149.99",
                in_stock=10,
                image1=self.make_test_image("updated.png"),
            ),
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertEqual(self.product.price_old, Decimal("99.99"))
        self.assertEqual(self.product.price_current, Decimal("149.99"))
        self.assertEqual(self.product.in_stock, 10)

    def test_put_returns_403_for_foreign_seller_product(self):
        foreign_user = User.objects.create_user(
            first_name="Foreign",
            last_name="Seller",
            email="foreign@example.com",
            password="StrongPass123",
            account_type="SELLER",
        )
        Seller.objects.create(
            user=foreign_user,
            business_name="Foreign Store",
            inn_identification_number="9999999999",
            phone_number="9999999999",
            business_address="Foreign street 1",
            city="Tomsk",
            postal_code="634000",
            bank_name="Foreign Bank",
            bank_bic_number="999999999",
            bank_current_account="99999999999999999999",
            bank_correspondent_account="88888888888888888888",
            is_approved=True,
        )
        self.client.force_authenticate(foreign_user)

        response = self.client.put(
            f"/sellers/products/{self.product.slug}/",
            self.get_product_payload(name=self.product.name),
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_soft_deletes_product(self):
        self.client.force_authenticate(self.other_user)

        response = self.client.delete(f"/sellers/products/{self.product.slug}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertTrue(self.product.is_deleted)

    def test_delete_returns_403_for_foreign_seller_product(self):
        foreign_user = User.objects.create_user(
            first_name="Foreign",
            last_name="Seller",
            email="foreign2@example.com",
            password="StrongPass123",
            account_type="SELLER",
        )
        Seller.objects.create(
            user=foreign_user,
            business_name="Foreign Store 2",
            inn_identification_number="7777777777",
            phone_number="7777777777",
            business_address="Foreign street 2",
            city="Tomsk",
            postal_code="634000",
            bank_name="Foreign Bank 2",
            bank_bic_number="777777777",
            bank_current_account="77777777777777777777",
            bank_correspondent_account="66666666666666666666",
            is_approved=True,
        )
        self.client.force_authenticate(foreign_user)

        response = self.client.delete(f"/sellers/products/{self.product.slug}/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class SellerOrdersViewTests(SellersBaseTestCase):
    def test_get_orders_returns_only_orders_with_current_seller_products(self):
        user_order = Order.objects.create(user=self.user)
        other_order = Order.objects.create(user=self.user)
        other_seller_user = User.objects.create_user(
            first_name="Second",
            last_name="Seller",
            email="secondseller@example.com",
            password="StrongPass123",
            account_type="SELLER",
        )
        other_seller = Seller.objects.create(
            user=other_seller_user,
            business_name="Second Store",
            inn_identification_number="5555555555",
            phone_number="5555555555",
            business_address="Second street 1",
            city="Tomsk",
            postal_code="634000",
            bank_name="Second Bank",
            bank_bic_number="555555555",
            bank_current_account="55555555555555555555",
            bank_correspondent_account="44444444444444444444",
            is_approved=True,
        )
        other_product = Product.objects.create(
            seller=other_seller,
            name="Other Product",
            desc="Other desc",
            price_current=Decimal("50.00"),
            category=self.category,
            in_stock=1,
            image1=self.make_test_image("other_product.png"),
        )
        OrderItem.objects.create(order=user_order, user=self.user, product=self.product, quantity=1)
        OrderItem.objects.create(order=other_order, user=self.user, product=other_product, quantity=1)
        self.client.force_authenticate(self.other_user)

        response = self.client.get("/sellers/orders/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["tx_ref"], user_order.tx_ref)

    def test_get_order_items_returns_only_current_seller_items(self):
        order = Order.objects.create(user=self.user)
        other_seller_user = User.objects.create_user(
            first_name="Second",
            last_name="Seller",
            email="secondseller2@example.com",
            password="StrongPass123",
            account_type="SELLER",
        )
        other_seller = Seller.objects.create(
            user=other_seller_user,
            business_name="Second Store 2",
            inn_identification_number="3333333333",
            phone_number="3333333333",
            business_address="Third street 1",
            city="Tomsk",
            postal_code="634000",
            bank_name="Third Bank",
            bank_bic_number="333333333",
            bank_current_account="33333333333333333333",
            bank_correspondent_account="22222222222222222222",
            is_approved=True,
        )
        other_product = Product.objects.create(
            seller=other_seller,
            name="Other Product 2",
            desc="Other desc 2",
            price_current=Decimal("75.00"),
            category=self.category,
            in_stock=1,
            image1=self.make_test_image("other_product2.png"),
        )
        OrderItem.objects.create(order=order, user=self.user, product=self.product, quantity=2)
        OrderItem.objects.create(order=order, user=self.user, product=other_product, quantity=1)
        self.client.force_authenticate(self.other_user)

        response = self.client.get(f"/sellers/orders/{order.tx_ref}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["quantity"], 2)
