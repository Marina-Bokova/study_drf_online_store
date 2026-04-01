from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.profiles.models import OrderItem
from apps.sellers.models import Seller
from apps.shop.models import Category, Product
from apps.shop.serializers import CategorySerializer, OrderItemSerializer, ProductSerializer, ToggleCartItemSerializer

tags = ["Shop"]


class CategoriesView(APIView):
    serializer_class = CategorySerializer

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

    @extend_schema(
        summary="Получение товаров в корзине",
        description="""
        Возвращает все товары в корзине текущего пользователя.
        """,
        tags=tags,
        responses=OrderItemSerializer,
    )
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response(data={"message": "Доступ запрещен."}, status=403)

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
        if not request.user.is_authenticated:
            return Response(data={"message": "Доступ запрещен."}, status=403)

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

        resp_message_substring = "Updated In"
        status_code = 200
        if created:
            status_code = 201
            resp_message_substring = "Added To"
        if orderitem.quantity == 0:
            resp_message_substring = "Removed From"
            orderitem.delete()
            data = None
        if resp_message_substring != "Removed From":
            serializer = self.serializer_class(orderitem)
            data = serializer.data
        return Response(data={"message": f"Item {resp_message_substring} Cart", "item": data}, status=status_code)
