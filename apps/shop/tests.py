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
from apps.shop.models import Category, Product, Review
from apps.shop.views import annotate_avg_rating


class ShopBaseTestCase(TestCase):
    @staticmethod
    def make_test_image(name="test.png"):
        buffer = BytesIO()
        Image.new("RGB", (1, 1), "white").save(buffer, format="PNG")
        return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")

    @classmethod
    def setUpTestData(cls):
        cls.seller_user = User.objects.create_user(
            first_name="Seller",
            last_name="User",
            email="seller@example.com",
            password="StrongPass123",
            account_type="SELLER",
        )
        cls.buyer = User.objects.create_user(
            first_name="Buyer",
            last_name="User",
            email="buyer@example.com",
            password="StrongPass123",
        )
        cls.other_buyer = User.objects.create_user(
            first_name="Other",
            last_name="Buyer",
            email="otherbuyer@example.com",
            password="StrongPass123",
        )
        cls.seller = Seller.objects.create(
            user=cls.seller_user,
            business_name="Tech Store",
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
            seller=cls.seller,
            name="Phone X",
            desc="Flagship phone",
            price_current=Decimal("99.99"),
            category=cls.category,
            in_stock=7,
            image1=cls.make_test_image("product.png"),
        )

    def setUp(self):
        self.client = APIClient()


class AnnotateAvgRatingTests(ShopBaseTestCase):
    def test_annotate_avg_rating_ignores_soft_deleted_reviews(self):
        Review.objects.create(user=self.buyer, product=self.product, rating=5, text="Great")
        deleted_review = Review.objects.create(
            user=self.other_buyer,
            product=self.product,
            rating=1,
            text="Bad",
        )
        deleted_review.delete()

        annotated_product = annotate_avg_rating(Product.objects.filter(id=self.product.id)).get()

        self.assertEqual(annotated_product.avg_rating, 5.0)


class ProductReviewsApiTests(ShopBaseTestCase):
    def test_create_review_returns_201_and_saves_review(self):
        self.client.force_authenticate(self.buyer)

        response = self.client.post(
            f"/shop/products/{self.product.slug}/reviews/",
            {"rating": 5, "text": "Excellent"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Review.objects.filter(user=self.buyer, product=self.product).count(), 1)
        self.assertEqual(response.data["rating"], 5)
        self.assertEqual(response.data["text"], "Excellent")

    def test_create_review_rejects_duplicate_review_from_same_user(self):
        Review.objects.create(user=self.buyer, product=self.product, rating=5, text="First")
        self.client.force_authenticate(self.buyer)

        response = self.client.post(
            f"/shop/products/{self.product.slug}/reviews/",
            {"rating": 4, "text": "Second"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Review.objects.filter(user=self.buyer, product=self.product).count(), 1)

    def test_review_owner_can_update_review(self):
        review = Review.objects.create(user=self.buyer, product=self.product, rating=5, text="First")
        self.client.force_authenticate(self.buyer)

        response = self.client.put(
            f"/shop/reviews/{review.id}/",
            {"rating": 4, "text": "Updated"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        review.refresh_from_db()
        self.assertEqual(review.rating, 4)
        self.assertEqual(review.text, "Updated")

    def test_review_non_owner_cannot_update_review(self):
        review = Review.objects.create(user=self.buyer, product=self.product, rating=5, text="First")
        self.client.force_authenticate(self.other_buyer)

        response = self.client.put(
            f"/shop/reviews/{review.id}/",
            {"rating": 3, "text": "Hack"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_delete_foreign_review(self):
        review = Review.objects.create(user=self.buyer, product=self.product, rating=5, text="First")
        admin = User.objects.create_user(
            first_name="Admin",
            last_name="User",
            email="admin@example.com",
            password="StrongPass123",
            is_staff=True,
        )
        self.client.force_authenticate(admin)

        response = self.client.delete(f"/shop/reviews/{review.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        review.refresh_from_db()
        self.assertTrue(review.is_deleted)


class CartApiTests(ShopBaseTestCase):
    def test_add_product_to_cart_creates_order_item(self):
        self.client.force_authenticate(self.buyer)

        response = self.client.post(
            "/shop/cart/",
            {"slug": self.product.slug, "quantity": 2},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(OrderItem.objects.filter(user=self.buyer, order__isnull=True).count(), 1)

        order_item = OrderItem.objects.get(user=self.buyer, order__isnull=True, product=self.product)
        self.assertEqual(order_item.quantity, 2)
        self.assertEqual(response.data["item"]["quantity"], 2)

    def test_setting_zero_quantity_removes_item_from_cart(self):
        OrderItem.objects.create(user=self.buyer, product=self.product, quantity=2)
        self.client.force_authenticate(self.buyer)

        response = self.client.post(
            "/shop/cart/",
            {"slug": self.product.slug, "quantity": 0},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(OrderItem.objects.filter(user=self.buyer, order__isnull=True).exists())
        self.assertIsNone(response.data["item"])

    def test_add_product_to_cart_returns_404_for_unknown_slug(self):
        self.client.force_authenticate(self.buyer)

        response = self.client.post(
            "/shop/cart/",
            {"slug": "missing-product", "quantity": 2},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class CheckoutApiTests(ShopBaseTestCase):
    def test_checkout_creates_order_from_cart_and_shipping_address(self):
        self.client.force_authenticate(self.buyer)
        cart_item = OrderItem.objects.create(user=self.buyer, product=self.product, quantity=3)
        shipping = ShippingAddress.objects.create(
            user=self.buyer,
            full_name="Buyer User",
            email="buyer@example.com",
            phone="123456789012",
            address="Lenina 1",
            city="Tomsk",
            country="Russia",
            zipcode="634000",
        )

        response = self.client.post(
            "/shop/checkout/",
            {"shipping_id": str(shipping.id)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        cart_item.refresh_from_db()
        order = cart_item.order
        self.assertIsNotNone(order)
        self.assertEqual(order.user, self.buyer)
        self.assertEqual(order.full_name, shipping.full_name)
        self.assertEqual(order.address, shipping.address)
        self.assertEqual(response.data["item"]["tx_ref"], order.tx_ref)

    def test_checkout_returns_400_when_cart_is_empty(self):
        self.client.force_authenticate(self.buyer)
        shipping = ShippingAddress.objects.create(
            user=self.buyer,
            full_name="Buyer User",
            email="buyer@example.com",
            phone="123456789012",
            address="Lenina 1",
            city="Tomsk",
            country="Russia",
            zipcode="634000",
        )

        response = self.client.post(
            "/shop/checkout/",
            {"shipping_id": str(shipping.id)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("message", response.data)

    def test_checkout_returns_404_for_missing_shipping_id(self):
        self.client.force_authenticate(self.buyer)
        OrderItem.objects.create(user=self.buyer, product=self.product, quantity=1)

        response = self.client.post(
            "/shop/checkout/",
            {"shipping_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_checkout_rejects_foreign_shipping_id(self):
        self.client.force_authenticate(self.buyer)
        OrderItem.objects.create(user=self.buyer, product=self.product, quantity=1)
        foreign_shipping = ShippingAddress.objects.create(
            user=self.other_buyer,
            full_name="Other Buyer",
            email="otherbuyer@example.com",
            phone="123456789012",
            address="Foreign 1",
            city="Tomsk",
            country="Russia",
            zipcode="634000",
        )

        response = self.client.post(
            "/shop/checkout/",
            {"shipping_id": str(foreign_shipping.id)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(Order.objects.filter(user=self.buyer, address="Foreign 1").exists())
