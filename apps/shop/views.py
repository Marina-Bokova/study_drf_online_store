from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsAdminOnly, IsOwnerOrAdmin
from apps.profiles.models import Order, OrderItem, ShippingAddress
from apps.sellers.models import Seller
from apps.shop.models import Category, Product
from apps.shop.serializers import (
    CategorySerializer,
    CheckoutSerializer,
    OrderItemSerializer,
    OrderSerializer,
    ProductSerializer,
    ToggleCartItemSerializer,
)

tags = ["Shop"]


class CategoriesView(APIView):
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOnly]

    @extend_schema(
        summary="Получение категории",
        description="""
        Возвращает все категории.
        """,
        tags=tags
    )
    def get(self, request, *args, **kwargs):
        categories = Category.objects.all()
        serializer = self.serializer_class(categories, many=True)
        return Response(data=serializer.data, status=200)

    @extend_schema(
        summary="Создание категории",
        description="""
        Позволяет создать новую категорию.
        """,
        tags=tags
    )
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            new_cat = Category.objects.create(**serializer.validated_data)
            serializer = self.serializer_class(new_cat)
            return Response(serializer.data, status=201)
        else:
            return Response(serializer.errors, status=400)


class ProductsByCategoryView(APIView):
    serializer_class = ProductSerializer

    @extend_schema(
        operation_id="category_products",
        summary="Получение товаров категории",
        description="""
        Возвращает все товары из одной категории по ее slug.
        """,
        tags=tags
    )
    def get(self, request, *args, **kwargs):
        category = Category.objects.get_or_none(slug=kwargs["slug"])
        if not category:
            return Response(data={"message": "Категория не найдена."}, status=404)

        products = Product.objects.select_related("category", "seller", "seller__user").filter(category=category)
        serializer = self.serializer_class(products, many=True)
        return Response(data=serializer.data, status=200)


class ProductsView(APIView):
    serializer_class = ProductSerializer

    @extend_schema(
        operation_id="all_products",
        summary="Получение всех товаров магазина",
        description="""
        Возвращает все товары интернет-магазина.
        """,
        tags=tags
    )
    def get(self, request, *args, **kwargs):
        products = Product.objects.select_related("category", "seller", "seller__user").all()
        serializer = self.serializer_class(products, many=True)
        return Response(data=serializer.data, status=200)


class ProductsBySellerView(APIView):
    serializer_class = ProductSerializer

    @extend_schema(
        summary="Получение товаров продавца",
        description="""
        Возвращает все товары одного продавца по его slug.
        """,
        tags=tags
    )
    def get(self, request, *args, **kwargs):
        seller = Seller.objects.get_or_none(slug=kwargs["slug"])
        if not seller:
            return Response(data={"message": "Продавец не найден."}, status=404)

        products = Product.objects.select_related("category", "seller", "seller__user").filter(seller=seller)
        serializer = self.serializer_class(products, many=True)
        return Response(data=serializer.data, status=200)


class ProductView(APIView):
    serializer_class = ProductSerializer

    def get_object(self, slug):
        product = Product.objects.get_or_none(slug=slug)
        return product

    @extend_schema(
        operation_id="product_detail",
        summary="Получение детальной информации о товаре",
        description="""
        Возвращает детальную информацию о товаре по его slug. 
        """,
        tags=tags
    )
    def get(self, request, *args, **kwargs):
        product = self.get_object(kwargs['slug'])
        if not product:
            return Response(data={"message": "Товар не найден."}, status=404)

        serializer = self.serializer_class(product)
        return Response(data=serializer.data, status=200)


class CartView(APIView):
    serializer_class = OrderItemSerializer
    permission_classes = [IsOwnerOrAdmin]

    @extend_schema(
        summary="Получение товаров в корзине",
        description="""
        Возвращает все товары в корзине текущего пользователя.
        """,
        tags=tags,
        responses=OrderItemSerializer,
    )
    def get(self, request, *args, **kwargs):
        cart_items = OrderItem.objects.select_related(
            "product", "product__seller", "product__seller__user"
        ).filter(user=request.user, order__isnull=True)
        serializer = self.serializer_class(cart_items, many=True)
        return Response(data=serializer.data, status=200)

    @extend_schema(
        summary="Добавление, обновление и удаление товара в корзине",
        description="""
        Добавляет товар в корзину, обновляет его количество или удаляет товар
        Если quantity равно 0, то товар удаляется автоматически.
        """,
        tags=tags,
        request=ToggleCartItemSerializer,
        responses=OrderItemSerializer,
    )
    def post(self, request, *args, **kwargs):
        serializer = ToggleCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        quantity = data["quantity"]

        product = Product.objects.select_related("seller", "seller__user").get_or_none(slug=data["slug"])
        if not product:
            return Response(data={"message": "Товар не найден."}, status=404)

        orderitem, created = OrderItem.objects.update_or_create(
            user=request.user,
            order=None,
            product=product,
            defaults={"quantity": quantity},
        )

        resp_message_substring = "в корзине обновлен"
        status_code = 200
        if created:
            status_code = 201
            resp_message_substring = "добавлен в корзину"
        if orderitem.quantity == 0:
            resp_message_substring = "удален из корзины"
            orderitem.delete()
            data = None
        if resp_message_substring != "удален из корзины":
            serializer = self.serializer_class(orderitem)
            data = serializer.data
        return Response(data={"message": f"Товар {resp_message_substring}", "item": data}, status=status_code)


class CheckoutView(APIView):
    serializer_class = CheckoutSerializer
    permission_classes = [IsOwnerOrAdmin]

    @extend_schema(
        summary="Создание заказа",
        description="""
        Создает заказ из текущей корзины пользователя и выбранного адреса доставки.
        """,
        tags=tags,
        request=CheckoutSerializer,
        responses=OrderSerializer,
    )
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart_items = OrderItem.objects.filter(user=request.user, order__isnull=True)
        if not cart_items.exists():
            return Response(data={"message": "Корзина пуста."}, status=400)

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        shipping_id = data.get("shipping_id")
        # Получаем информацию о доставке на основе идентификатора доставки, введенного пользователем.
        shipping = ShippingAddress.objects.get_or_none(id=shipping_id)
        if not shipping:
            return Response({"message": "No shipping address with that ID"}, status=404)

        fields_to_update = [
            "full_name",
            "email",
            "phone",
            "address",
            "city",
            "country",
            "zipcode",
        ]
        data = {}
        for field in fields_to_update:
            value = getattr(shipping, field)
            data[field] = value

        order = Order.objects.create(user=request.user, **data)
        cart_items.update(order=order)

        serializer = OrderSerializer(order)
        return Response(data={"message": "Заказ успешно оформлен", "item": serializer.data}, status=201)
