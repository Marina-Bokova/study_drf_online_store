from drf_spectacular.utils import OpenApiParameter, OpenApiTypes


PRODUCT_PARAM_EXAMPLE = [
    OpenApiParameter(
        name="max_price",
        description="Показать товары с ценой не более заданной",
        required=False,
        type=OpenApiTypes.INT,
    ),
    OpenApiParameter(
        name="min_price",
        description="Показать товары с ценой не менее заданной",
        required=False,
        type=OpenApiTypes.INT,
    ),
    OpenApiParameter(
        name="in_stock",
        description="Показать товары, количество которых не менее заданного",
        required=False,
        type=OpenApiTypes.INT,
    ),
    OpenApiParameter(
        name="created_at",
        description="Показать товары, созданные не ранее заданной даты",
        required=False,
        type=OpenApiTypes.DATE,
    ),
]