from autoslug import AutoSlugField
from django.db import models
from slugify import slugify

from apps.accounts.models import User
from apps.common.models import BaseModel


class Seller(BaseModel):
    """
    Информация о бизнесе, связанном с профилем продавца

    Attributes:
        user (OneToOneField): Пользователь, которому принадлежит бизнес
        business_name (str): Название бизнеса продавца
        slug (str): Уникальный slug, генерируемый на основе business_name
        inn_identification_number (str): Идентификационный номер налогоплательщика (ИНН)
        website_url (str): URL-адрес сайта бизнеса
        phone_number (str): Номер телефона
        business_description (str): Описание бизнеса

        business_address (str): Адрес бизнеса
        city (str): Город
        postal_code (str): Почтовый индекс

        bank_name (str): Название банка
        bank_bic_number (str): БИК банка
        bank_current_account (str): Номер расчетного счета
        bank_correspondent_account (str): Номер корреспондентского счета

        is_approved (bool): Поле для указания, проверен ли продавец или нет

    Methods:
        __str__(): Возвращает строковое представление объекта Seller
    """

    # Связь с моделью пользователя
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="seller")

    # Информация о бизнесе
    business_name = models.CharField(max_length=255)
    slug = AutoSlugField(populate_from="business_name", always_update=True, unique=True, null=True, blank=True,
                         slugify=slugify)
    inn_identification_number = models.CharField(max_length=50)
    website_url = models.URLField(null=True, blank=True)
    phone_number = models.CharField(max_length=20)
    business_description = models.TextField(null=True, blank=True)

    # Адрес магазина
    business_address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)

    # Банковская информация
    bank_name = models.CharField(max_length=255)
    bank_bic_number = models.CharField(max_length=9)
    bank_current_account = models.CharField(max_length=20)
    bank_correspondent_account = models.CharField(max_length=20)

    # Статус
    is_approved = models.BooleanField(default=False)

    def __str__(self):
        return f"Продавец: {self.business_name}"
