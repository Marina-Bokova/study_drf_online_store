from autoslug import AutoSlugField
from django.db import models
from slugify import slugify

from apps.accounts.models import User
from apps.common.models import BaseModel, IsDeletedModel
from apps.sellers.models import Seller


RATING_CHOICES = (
    (1, 1),
    (2, 2),
    (3, 3),
    (4, 4),
    (5, 5),
)


class Category(BaseModel):
    """
    Категория товара

    Атрибуты:
        name (str): Название категории, уникальное для каждого экземпляра
        slug (str): Уникальный slug, генерируемый на основе name
        image (ImageField): Изображение, представляющее категорию

    Методы:
        __str__(): Возвращает строковое представление объекта Category
    """

    name = models.CharField(max_length=100, unique=True)
    slug = AutoSlugField(populate_from="name", unique=True, always_update=True, slugify=slugify)
    image = models.ImageField(upload_to='category_images/')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"


class Product(IsDeletedModel):
    """
    Товар, выставленный на продажу

    Attributes:
        seller (ForeignKey): Пользователь, продающий товар
        name (str): Название товара
        slug (str): Уникальный slug, генерируемый на основе name, используемый в URL-адресах
        desc (str): Описание товара
        price_old (Decimal): Первоначальная цена товара
        price_current (Decimal): Текущая цена товара
        category (ForeignKey): Категория, к которой относится товар
        in_stock (int): Количество товара на складе
        image1 (ImageField): Первое изображение товара
        image2 (ImageField): Второе изображение товара
        image3 (ImageField): Третье изображение товара

    Methods:
        __str__(): Возвращает строковое представление объекта Product
    """

    seller = models.ForeignKey(Seller, on_delete=models.SET_NULL, related_name="products", null=True)
    name = models.CharField(max_length=100)
    slug = AutoSlugField(populate_from="name", unique=True, db_index=True, slugify=slugify)
    desc = models.TextField()
    price_old = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    price_current = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, related_name="products", null=True)
    in_stock = models.IntegerField(default=5)

    # Допустимо не менее 1 и не более 3 изображений товара
    image1 = models.ImageField(upload_to='product_images/')
    image2 = models.ImageField(upload_to='product_images/', blank=True)
    image3 = models.ImageField(upload_to='product_images/', blank=True)

    def __str__(self):
        return self.name


class Review(IsDeletedModel):
    """
    Комментарий пользователя к товару

    Attributes:
        user (ForeignKey): Пользователь, оставляющий комментарий
        product (ForeignKey): Товар, к которому оставляют отзыв
        rating (int): оценка товара по 5-бальной шкале
        text (str): Текстовый комментарий к товару

    Methods:
        __str__(): Возвращает строковое представление объекта Review
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    rating = models.IntegerField(choices=RATING_CHOICES)
    text = models.TextField()

    def __str__(self):
        return f"{self.user} - {self.product} ({self.rating})"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "product"],
                condition=models.Q(is_deleted=False),
                name="unique_user_product_review",
            )
        ]

