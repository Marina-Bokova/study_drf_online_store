from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from apps.common.permissions import IsOwnerOrAdmin, IsSeller
from apps.common.utils import generate_unique_code, set_dict_attr


class GenerateUniqueCodeTests(SimpleTestCase):
    def test_generate_unique_code_returns_code_when_it_is_unique_on_first_try(self):
        model = Mock()
        model.objects.filter.return_value.exists.return_value = False

        with patch("apps.common.utils.secrets.choice", return_value="Z"):
            code = generate_unique_code(model, "tx_ref")

        self.assertEqual(code, "ZZZZZZZZZZZZ")
        model.objects.filter.assert_called_once_with(tx_ref="ZZZZZZZZZZZZ")
        model.objects.filter.return_value.exists.assert_called_once()

    def test_generate_unique_code_retries_until_code_is_unique(self):
        model = Mock()
        model.objects.filter.return_value.exists.side_effect = [True, False]

        with patch("apps.common.utils.secrets.choice", side_effect=["A"] * 12 + ["B"] * 12):
            code = generate_unique_code(model, "tx_ref")

        self.assertEqual(code, "BBBBBBBBBBBB")
        self.assertEqual(model.objects.filter.call_count, 2)
        model.objects.filter.assert_any_call(tx_ref="AAAAAAAAAAAA")
        model.objects.filter.assert_any_call(tx_ref="BBBBBBBBBBBB")

    def test_generate_unique_code_uses_requested_field_name_for_lookup(self):
        model = Mock()
        model.objects.filter.return_value.exists.return_value = False

        with patch("apps.common.utils.secrets.choice", return_value="Q"):
            code = generate_unique_code(model, "order_code")

        self.assertEqual(code, "QQQQQQQQQQQQ")
        model.objects.filter.assert_called_once_with(order_code="QQQQQQQQQQQQ")

    def test_generate_unique_code_builds_twelve_character_code(self):
        model = Mock()
        model.objects.filter.return_value.exists.return_value = False

        code = generate_unique_code(model, "tx_ref")

        self.assertEqual(len(code), 12)


class SetDictAttrTests(SimpleTestCase):
    def test_set_dict_attr_assigns_all_values_and_returns_object(self):
        obj = SimpleNamespace()

        result = set_dict_attr(obj, {"name": "Phone", "price": 199.99})

        self.assertIs(result, obj)
        self.assertEqual(obj.name, "Phone")
        self.assertEqual(obj.price, 199.99)


class PermissionTests(SimpleTestCase):
    def test_is_owner_or_admin_allows_owner(self):
        permission = IsOwnerOrAdmin()
        user = SimpleNamespace(is_authenticated=True, is_staff=False)
        request = SimpleNamespace(user=user)
        obj = SimpleNamespace(user=user)

        self.assertTrue(permission.has_permission(request, view=None))
        self.assertTrue(permission.has_object_permission(request, view=None, obj=obj))

    def test_is_seller_requires_approved_seller_profile(self):
        permission = IsSeller()
        user = SimpleNamespace(
            is_authenticated=True,
            is_staff=False,
            account_type="SELLER",
            seller=SimpleNamespace(is_approved=False),
        )
        request = SimpleNamespace(user=user)

        self.assertFalse(permission.has_permission(request, view=None))

        user.seller.is_approved = True

        self.assertTrue(permission.has_permission(request, view=None))
