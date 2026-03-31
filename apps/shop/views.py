from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.sellers.models import Seller
from apps.shop.models import Category, Product
from apps.shop.serializers import CategorySerializer, ProductSerializer

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
