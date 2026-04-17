from decimal import Decimal
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.common.test_utils import TempMediaRootMixin
from apps.profiles.models import Order, OrderItem, ShippingAddress
from apps.sellers.models import Seller
from apps.shop.models import Category, Product


class ProfilesBaseTestCase(TempMediaRootMixin, TestCase):
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
            last_name="Buyer",
            email="otherbuyer@example.com",
            password="StrongPass123",
        )
        cls.seller_user = User.objects.create_user(
            first_name="Seller",
            last_name="User",
            email="seller@example.com",
            password="StrongPass123",
            account_type="SELLER",
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
            in_stock=5,
            image1=cls.make_test_image("product.png"),
        )

    def setUp(self):
        self.client = APIClient()


class OrderModelTests(ProfilesBaseTestCase):
    def test_order_save_generates_tx_ref_on_create_and_keeps_it_on_update(self):
        order = Order.objects.create(user=self.user)
        original_tx_ref = order.tx_ref

        order.delivery_status = "PACKING"
        order.save()
        order.refresh_from_db()

        self.assertEqual(order.tx_ref, original_tx_ref)

    def test_order_totals_are_calculated_from_related_items(self):
        order = Order.objects.create(user=self.user)
        OrderItem.objects.create(order=order, user=self.user, product=self.product, quantity=2)
        OrderItem.objects.create(order=order, user=self.user, product=self.product, quantity=1)

        self.assertEqual(order.get_cart_subtotal, Decimal("299.97"))
        self.assertEqual(order.get_cart_total, Decimal("299.97"))

    def test_order_item_total_uses_product_price_and_quantity(self):
        order = Order.objects.create(user=self.user)
        item = OrderItem.objects.create(order=order, user=self.user, product=self.product, quantity=3)

        self.assertEqual(item.get_total, Decimal("299.97"))


class ProfileApiTests(ProfilesBaseTestCase):
    def test_get_profile_returns_authenticated_user_data(self):
        self.client.force_authenticate(self.user)

        response = self.client.get("/profiles/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], self.user.email)
        self.assertEqual(response.data["first_name"], self.user.first_name)

    def test_put_profile_updates_names(self):
        self.client.force_authenticate(self.user)

        response = self.client.put(
            "/profiles/",
            {
                "first_name": "Marina",
                "last_name": "Star",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Marina")
        self.assertEqual(self.user.last_name, "Star")

    def test_delete_profile_deactivates_user(self):
        self.client.force_authenticate(self.user)

        response = self.client.delete("/profiles/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)


class ShippingAddressApiTests(ProfilesBaseTestCase):
    def get_shipping_payload(self, **overrides):
        payload = {
            "full_name": "Buyer User",
            "email": "buyer@example.com",
            "phone": "123456789012",
            "address": "Lenina 1",
            "city": "Tomsk",
            "country": "Russia",
            "zipcode": "634000",
        }
        payload.update(overrides)
        return payload

    def test_post_shipping_address_creates_address_for_user(self):
        self.client.force_authenticate(self.user)

        response = self.client.post(
            "/profiles/shipping_addresses/",
            self.get_shipping_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ShippingAddress.objects.filter(user=self.user).count(), 1)
        self.assertEqual(response.data["city"], "Tomsk")

    def test_put_shipping_address_updates_existing_address(self):
        shipping = ShippingAddress.objects.create(user=self.user, **self.get_shipping_payload())
        self.client.force_authenticate(self.user)

        response = self.client.put(
            f"/profiles/shipping_addresses/detail/{shipping.id}/",
            self.get_shipping_payload(city="Moscow"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        shipping.refresh_from_db()
        self.assertEqual(shipping.city, "Moscow")

    def test_get_shipping_address_returns_400_for_invalid_uuid(self):
        self.client.force_authenticate(self.user)

        response = self.client.get("/profiles/shipping_addresses/detail/not-a-uuid/")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("message", response.data)

    def test_get_shipping_addresses_returns_only_current_user_addresses(self):
        ShippingAddress.objects.create(user=self.user, **self.get_shipping_payload())
        ShippingAddress.objects.create(
            user=self.other_user,
            **self.get_shipping_payload(email="other@example.com", city="Paris"),
        )
        self.client.force_authenticate(self.user)

        response = self.client.get("/profiles/shipping_addresses/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["email"], "buyer@example.com")

    def test_get_shipping_address_returns_404_for_foreign_address(self):
        shipping = ShippingAddress.objects.create(user=self.other_user, **self.get_shipping_payload())
        self.client.force_authenticate(self.user)

        response = self.client.get(f"/profiles/shipping_addresses/detail/{shipping.id}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_shipping_address_removes_address(self):
        shipping = ShippingAddress.objects.create(user=self.user, **self.get_shipping_payload())
        self.client.force_authenticate(self.user)

        response = self.client.delete(f"/profiles/shipping_addresses/detail/{shipping.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(ShippingAddress.objects.filter(id=shipping.id).exists())


class OrdersApiTests(ProfilesBaseTestCase):
    def test_get_orders_returns_only_current_user_orders(self):
        user_order = Order.objects.create(user=self.user)
        other_order = Order.objects.create(user=self.other_user)
        OrderItem.objects.create(order=user_order, user=self.user, product=self.product, quantity=2)
        OrderItem.objects.create(order=other_order, user=self.other_user, product=self.product, quantity=1)
        self.client.force_authenticate(self.user)

        response = self.client.get("/profiles/orders/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["tx_ref"], user_order.tx_ref)

    def test_get_order_items_returns_only_for_owners_order(self):
        order = Order.objects.create(user=self.user)
        OrderItem.objects.create(order=order, user=self.user, product=self.product, quantity=2)
        self.client.force_authenticate(self.user)

        response = self.client.get(f"/profiles/orders/{order.tx_ref}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["quantity"], 2)

    def test_get_order_items_returns_404_for_foreign_order(self):
        other_order = Order.objects.create(user=self.other_user)
        OrderItem.objects.create(order=other_order, user=self.other_user, product=self.product, quantity=1)
        self.client.force_authenticate(self.user)

        response = self.client.get(f"/profiles/orders/{other_order.tx_ref}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
