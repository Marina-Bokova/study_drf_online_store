from django.db import models

from apps.accounts.models import User
from apps.common.models import BaseModel
from apps.common.utils import generate_unique_code
from apps.shop.models import Product


class ShippingAddress(BaseModel):
    """
    Адрес доставки, указанный Покупателем

    Атрибуты:
        user (ForeignKey): Пользователь, которому принадлежит адрес доставки
        full_name (str): Полное имя получателя
        email (str): Адрес электронной почты получателя
        phone (str): Номер телефона получателя
        address (str): Адрес доставки
        city (str): Город доставки
        country (str): Страна доставки
        zipcode (str): Почтовый индекс места доставки

    Методы:
        __str__():
            Возвращает строковое представление данных о доставке.
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="shipping_addresses"
    )
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=12)
    address = models.CharField(max_length=1000)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=200)
    zipcode = models.CharField(max_length=6)

    def __str__(self):
        return f"Адрес доставки для пользователя {self.full_name}"


DELIVERY_STATUS_CHOICES = (
    ("PENDING", "ОЖИДАНИЕ"),
    ("PACKING", "УПАКОВКА"),
    ("SHIPPING", "В ПУТИ"),
    ("ARRIVING", "ГОТОВ К ВЫДАЧЕ"),
    ("SUCCESS", "ВЫПОЛНЕН"),
)

PAYMENT_STATUS_CHOICES = (
    ("PENDING", "ОЖИДАНИЕ"),
    ("PROCESSING", "ОБРАБОТКА"),
    ("SUCCESSFUL", "ОПЛАЧЕНО"),
    ("CANCELLED", "ОТМЕНЕН"),
    ("FAILED", "ОШИБКА"),
)


class Order(BaseModel):
    """
    Заказ клиента

    Attributes:
        user (ForeignKey): Пользователь, оформивший заказ
        tx_ref (str): Уникальный идентификатор транзакции
        delivery_status (str): Статус доставки заказа
        payment_status (str): Статус оплаты заказа
        date_delivered (DateTimeField): Временная метка доставки заказа

    Methods:
        __str__():
            Возвращает строковое представление объекта Order
        save(*args, **kwargs):
            Переопределяет метод сохранения для генерации уникальной ссылки на транзакцию при создании нового заказа
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    tx_ref = models.CharField(max_length=100, blank=True, unique=True)
    delivery_status = models.CharField(
        max_length=20, default="PENDING", choices=DELIVERY_STATUS_CHOICES
    )
    payment_status = models.CharField(
        max_length=20, default="PENDING", choices=PAYMENT_STATUS_CHOICES
    )
    date_delivered = models.DateTimeField(null=True, blank=True)

    # Адрес доставки (если поля пустые, то данные будут подставлены из значений модели ShippingAddress)
    full_name = models.CharField(max_length=1000, null=True)
    email = models.EmailField(null=True)
    phone = models.CharField(max_length=20, null=True)
    address = models.CharField(max_length=1000, null=True)
    city = models.CharField(max_length=200, null=True)
    country = models.CharField(max_length=100, null=True)
    zipcode = models.CharField(max_length=6, null=True)

    def __str__(self):
        return f"{self.user.full_name}'s order"

    def save(self, *args, **kwargs) -> None:
        if not self.created_at:
            self.tx_ref = generate_unique_code(Order, "tx_ref")
        super().save(*args, **kwargs)


class OrderItem(BaseModel):
    """
    Товар в заказе.

    Attributes:
        user (ForeignKey): Пользователь, к которому относится этот товар (используется для хранения товара в корзине)
        order (ForeignKey): Заказ, к которому относится этот товар
        product (ForeignKey): Товар, связанный с этим товаром в заказе
        quantity (int): Количество заказанного товара

    Methods:
        __str__():
            Возвращает строковое представление позиции товара - название продукта
        get_total():
            Возвращает общую стоимость позиции товара
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    order = models.ForeignKey(
        Order,
        related_name="orderitems",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.product.name

    @property
    def get_total(self):
        return self.product.price_current * self.quantity