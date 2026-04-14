from django.db.models import Avg, Q
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.paginations import CustomPagination
from apps.common.permissions import IsAdminOnly, IsOwnerOrAdmin, IsBuyer
from apps.common.utils import set_dict_attr
from apps.profiles.models import Order, OrderItem, ShippingAddress
from apps.sellers.models import Seller
from apps.shop.filters import ProductFilter
from apps.shop.models import Category, Product, Review
from apps.shop.schema_examples import PRODUCT_PARAM_EXAMPLE
from apps.shop.serializers import (
    CategorySerializer,
    CheckoutSerializer,
    OrderItemSerializer,
    OrderSerializer,
    ProductSerializer,
    ReviewCreateUpdateSerializer,
    ReviewSerializer,
    ToggleCartItemSerializer,
)

tags = ["Shop"]


def annotate_avg_rating(queryset):
    return queryset.annotate(
        avg_rating=Avg("reviews__rating", filter=Q(reviews__is_deleted=False))
    )


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
        return Response(data=serializer.data, status=status.HTTP_200_OK)

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
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
            return Response(data={"message": "Категория не найдена."}, status=status.HTTP_404_NOT_FOUND)

        products = annotate_avg_rating(
            Product.objects.select_related("category", "seller", "seller__user").filter(category=category)
        )
        serializer = self.serializer_class(products, many=True)
        return Response(data=serializer.data, status=status.HTTP_200_OK)


class ProductsView(APIView):
    serializer_class = ProductSerializer
    pagination_class = CustomPagination

    @extend_schema(
        operation_id="all_products",
        summary="Получение всех товаров магазина",
        description="""
        Возвращает все товары интернет-магазина.
        """,
        tags=tags,
        parameters=PRODUCT_PARAM_EXAMPLE,
    )
    def get(self, request, *args, **kwargs):
        products = annotate_avg_rating(
            Product.objects.select_related("category", "seller", "seller__user").all()
        )

        filterset = ProductFilter(request.GET, queryset=products)
        if filterset.is_valid():
            queryset = filterset.qs
            paginator = self.pagination_class()
            paginated_queryset = paginator.paginate_queryset(queryset, request)
            serializer = self.serializer_class(paginated_queryset, many=True)
            return paginator.get_paginated_response(serializer.data)
        else:
            return Response(filterset.errors, status=status.HTTP_400_BAD_REQUEST)


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
            return Response(data={"message": "Продавец не найден."}, status=status.HTTP_404_NOT_FOUND)

        products = annotate_avg_rating(
            Product.objects.select_related("category", "seller", "seller__user").filter(seller=seller)
        )
        serializer = self.serializer_class(products, many=True)
        return Response(data=serializer.data, status=status.HTTP_200_OK)


class ProductView(APIView):
    serializer_class = ProductSerializer

    def get_object(self, slug):
        product = annotate_avg_rating(
            Product.objects.select_related("category", "seller", "seller__user")
        ).get_or_none(slug=slug)
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
            return Response(data={"message": "Товар не найден."}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.serializer_class(product)
        return Response(data=serializer.data, status=status.HTTP_200_OK)


class ProductReviewsView(APIView):
    serializer_class = ReviewSerializer
    permission_classes = [IsBuyer]

    def get_product(self, slug):
        return Product.objects.get_or_none(slug=slug)

    @extend_schema(
        summary="Получение отзывов о товаре",
        description="""
        Возвращает все отзывы, оставленные к товару по его slug.
        """,
        tags=tags,
        responses=ReviewSerializer,
    )
    def get(self, request, *args, **kwargs):
        product = self.get_product(kwargs["slug"])
        if not product:
            return Response(data={"message": "Товар не найден."}, status=status.HTTP_404_NOT_FOUND)

        reviews = Review.objects.select_related("user").filter(product=product)
        serializer = self.serializer_class(reviews, many=True)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Создание отзыва о товаре",
        description="""
        Позволяет авторизованному пользователю оставить один отзыв на товар.
        """,
        tags=tags,
        request=ReviewCreateUpdateSerializer,
        responses=ReviewSerializer,
    )
    def post(self, request, *args, **kwargs):
        product = self.get_product(kwargs["slug"])
        if not product:
            return Response(data={"message": "Товар не найден."}, status=status.HTTP_404_NOT_FOUND)

        if Review.objects.filter(user=request.user, product=product).exists():
            return Response(
                data={"message": "Вы уже оставили отзыв на этот товар"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ReviewCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        review = Review.objects.create(user=request.user, product=product, **serializer.validated_data)
        response_serializer = self.serializer_class(review)
        return Response(data=response_serializer.data, status=status.HTTP_201_CREATED)


class ReviewDetailView(APIView):
    serializer_class = ReviewSerializer
    permission_classes = [IsOwnerOrAdmin]

    def get_object(self, request, review_id):
        review = Review.objects.select_related("user", "product").get_or_none(id=review_id)
        if not review:
            return None
        self.check_object_permissions(request, review)
        return review

    @extend_schema(
        summary="Изменение отзыва",
        description="""
        Позволяет владельцу или администратору изменить отзыв.
        """,
        tags=tags,
        request=ReviewCreateUpdateSerializer,
        responses=ReviewSerializer,
    )
    def put(self, request, *args, **kwargs):
        review = self.get_object(request, kwargs["id"])
        if not review:
            return Response(data={"message": "Отзыв не найден."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ReviewCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = set_dict_attr(review, serializer.validated_data)
        review.save()
        response_serializer = self.serializer_class(review)
        return Response(data=response_serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Удаление отзыва",
        description="""
        Позволяет владельцу или администратору удалить отзыв.
        """,
        tags=tags,
    )
    def delete(self, request, *args, **kwargs):
        review = self.get_object(request, kwargs["id"])
        if not review:
            return Response(data={"message": "Отзыв не найден."}, status=status.HTTP_404_NOT_FOUND)

        review.delete()
        return Response(data={"message": "Отзыв успешно удален."}, status=status.HTTP_200_OK)


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
        return Response(data=serializer.data, status=status.HTTP_200_OK)

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
            return Response(data={"message": "Товар не найден."}, status=status.HTTP_404_NOT_FOUND)

        orderitem, created = OrderItem.objects.update_or_create(
            user=request.user,
            order=None,
            product=product,
            defaults={"quantity": quantity},
        )

        resp_message_substring = "в корзине обновлен"
        status_code = status.HTTP_200_OK
        if created:
            status_code = status.HTTP_201_CREATED
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
            return Response(data={"message": "Корзина пуста."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        shipping_id = data.get("shipping_id")
        # Получаем информацию о доставке на основе идентификатора доставки, введенного пользователем.
        shipping = ShippingAddress.objects.get_or_none(id=shipping_id, user=request.user)
        if not shipping:
            return Response({"message": "No shipping address with that ID"}, status=status.HTTP_404_NOT_FOUND)

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
        return Response(data={"message": "Заказ успешно оформлен", "item": serializer.data},
                        status=status.HTTP_201_CREATED)
