from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.utils import set_dict_attr
from apps.sellers.models import Seller
from apps.sellers.serializers import SellerSerializer
from apps.shop.models import Product, Category
from apps.shop.serializers import ProductSerializer, CreateProductSerializer

tags = ["Sellers"]


class SellersView(APIView):
    serializer_class = SellerSerializer

    @extend_schema(
        summary="Подача заявки, чтобы стать продавцом.",
        description="""
        Позволяет покупателю подать заявку на то, чтобы стать продавцом.
        """,
        tags=tags)

    def post(self, request):
        user = request.user
        serializer = self.serializer_class(data=request.data, partial=False)
        if serializer.is_valid():
            data = serializer.validated_data
            seller, _ = Seller.objects.update_or_create(user=user, defaults=data)
            user.account_type = 'SELLER'
            user.save()
            serializer = self.serializer_class(seller)
            return Response(data=serializer.data, status=201)
        else:
            return Response(data=serializer.errors, status=400)


class SellerProductsView(APIView):
    serializer_class = ProductSerializer

    @extend_schema(
        summary="Получение товаров продавца",
        description="""
        Возвращает все товары указанного продавца.
        Товары можно фильтровать по названию, размеру или цвету.
        """,
        tags=tags,
    )
    def get(self, request, *args, **kwargs):
        seller = Seller.objects.get_or_none(user=request.user, is_approved=True)
        if not seller:
            return Response(data={"message": "Доступ запрещен"}, status=403)
        products = Product.objects.select_related("category", "seller", "seller__user").filter(seller=seller)
        serializer = self.serializer_class(products, many=True)
        return Response(data=serializer.data, status=200)

    @extend_schema(
        summary="Добавление продукта",
        description="""
        Позволяет продавцу создать новый товар.
        """,
        tags=tags,
        request=CreateProductSerializer,
        responses=ProductSerializer,
    )
    def post(self, request, *args, **kwargs):
        serializer = CreateProductSerializer(data=request.data)
        seller = Seller.objects.get_or_none(user=request.user, is_approved=True)
        if not seller:
            return Response(data={"message": "Доступ запрещен"}, status=403)
        if serializer.is_valid():
            data = serializer.validated_data
            category_slug = data.pop("category_slug", None)
            category = Category.objects.get_or_none(slug=category_slug)
            if not category:
                return Response(data={"message": "Указанной категории не существует."}, status=404)
            data['category'] = category
            data['seller'] = seller
            new_prod = Product.objects.create(**data)
            serializer = ProductSerializer(new_prod)
            return Response(serializer.data, status=201)
        else:
            return Response(serializer.errors, status=400)


class SellerProductView(APIView):
    serializer_class = CreateProductSerializer

    def get_object(self, slug):
        product = Product.objects.get_or_none(slug=slug)
        return product

    @extend_schema(
        summary="Обновление товара продавца",
        description="""
        Позволяет продавцу обновить свой товар по slug.
        """,
        tags=tags,
        request=CreateProductSerializer,
        responses=ProductSerializer,
    )
    def put(self, request, *args, **kwargs):
        product = self.get_object(kwargs['slug'])
        if not product:
            return Response(data={"message": "Товар не найден."}, status=404)
        if not product.seller or product.seller.user != request.user:
            return Response(data={"message": "Доступ запрещен."}, status=403)

        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data

            category_slug = data.pop("category_slug", None)
            category = Category.objects.get_or_none(slug=category_slug)
            if not category:
                return Response(data={"message": "Category does not exist!"}, status=404)
            data['category'] = category

            if data["price_current"] != product.price_current:
                data["price_old"] = product.price_current
            product = set_dict_attr(product, data)
            product.save()
            serializer = ProductSerializer(product)
            return Response(data=serializer.data, status=200)
        else:
            return Response(data=serializer.errors, status=400)


    @extend_schema(
        summary="Удаление товара продавца",
        description="""
        Позволяет продавцу удалить свой товар по slug.
        """,
        tags=tags,
    )
    def delete(self, request, *args, **kwargs):
        product = self.get_object(kwargs['slug'])
        if not product:
            return Response(data={"message": "Товар не найден."}, status=404)
        if not product.seller or product.seller.user != request.user:
            return Response(data={"message": "Доступ запрещен."}, status=403)
        product.delete()
        return Response(data={"message": "Информация о товаре успешно удалена."}, status=200)
