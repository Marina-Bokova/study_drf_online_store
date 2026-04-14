from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.accounts.serializers import CreateUserSerializer, MyTokenObtainPairSerializer


class CreateUserSerializerTests(TestCase):
    def test_serializer_creates_user_with_hashed_password(self):
        serializer = CreateUserSerializer(
            data={"email": "buyer@example.com", "password": "StrongPass123"}
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()

        self.assertEqual(user.email, "buyer@example.com")
        self.assertTrue(user.check_password("StrongPass123"))
        self.assertEqual(user.account_type, "BUYER")


class RegistrationApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("registration")

    def test_registration_returns_201_and_creates_user(self):
        response = self.client.post(
            self.url,
            {"email": "newuser@example.com", "password": "StrongPass123"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, {"message": "success"})
        self.assertTrue(User.objects.filter(email="newuser@example.com").exists())
        self.assertTrue(
            User.objects.get(email="newuser@example.com").check_password("StrongPass123")
        )

    def test_registration_returns_400_for_invalid_password(self):
        response = self.client.post(
            self.url,
            {"email": "newuser@example.com", "password": "12345678"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)
        self.assertFalse(User.objects.filter(email="newuser@example.com").exists())

    def test_registration_returns_400_when_email_is_missing(self):
        response = self.client.post(
            self.url,
            {"password": "StrongPass123"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)


class TokenTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.token_url = reverse("token_obtain_pair")
        self.refresh_url = reverse("token_refresh")
        self.verify_url = reverse("token_verify")

    def test_token_serializer_adds_admin_group_for_staff(self):
        user = User.objects.create_user(
            first_name="Admin",
            last_name="User",
            email="admin@example.com",
            password="StrongPass123",
            is_staff=True,
        )

        token = MyTokenObtainPairSerializer.get_token(user)

        self.assertEqual(token["group"], "admin")
        self.assertNotIn("role", token)

    def test_token_serializer_adds_user_group_and_role_for_buyer(self):
        user = User.objects.create_user(
            first_name="Buyer",
            last_name="User",
            email="buyer@example.com",
            password="StrongPass123",
            account_type="BUYER",
        )

        token = MyTokenObtainPairSerializer.get_token(user)

        self.assertEqual(token["group"], "user")
        self.assertEqual(token["role"], "BUYER")

    def test_token_endpoint_returns_access_and_refresh_tokens(self):
        user = User.objects.create_user(
            first_name="Buyer",
            last_name="User",
            email="buyer@example.com",
            password="StrongPass123",
        )

        response = self.client.post(
            self.token_url,
            {"email": user.email, "password": "StrongPass123"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_token_endpoint_rejects_invalid_password(self):
        user = User.objects.create_user(
            first_name="Buyer",
            last_name="User",
            email="buyer@example.com",
            password="StrongPass123",
        )

        response = self.client.post(
            self.token_url,
            {"email": user.email, "password": "WrongPass123"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_endpoint_returns_new_access_token(self):
        user = User.objects.create_user(
            first_name="Buyer",
            last_name="User",
            email="buyer@example.com",
            password="StrongPass123",
        )
        token_response = self.client.post(
            self.token_url,
            {"email": user.email, "password": "StrongPass123"},
            format="json",
        )

        response = self.client.post(
            self.refresh_url,
            {"refresh": token_response.data["refresh"]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_verify_endpoint_accepts_valid_access_token(self):
        user = User.objects.create_user(
            first_name="Buyer",
            last_name="User",
            email="buyer@example.com",
            password="StrongPass123",
        )
        token_response = self.client.post(
            self.token_url,
            {"email": user.email, "password": "StrongPass123"},
            format="json",
        )

        response = self.client.post(
            self.verify_url,
            {"token": token_response.data["access"]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
