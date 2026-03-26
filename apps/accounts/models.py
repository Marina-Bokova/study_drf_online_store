from django.db import models
from django.contrib.auth.models import AbstractBaseUser

from apps.accounts.managers import CustomUserManager
from apps.common.models import IsDeletedModel


ACCOUNT_TYPE_CHOICES = (
    ("SELLER", "Продавец"),
    ("BUYER", "Покупатель"),
)


class User(IsDeletedModel, AbstractBaseUser):
    """
    Кастомная модель пользователя, созданная на основе AbstractBaseUser

    Attributes:
        first_name (str): Имя пользователя
        last_name (str): Фамилия пользователя
        email (str): Адрес электронной почты, используемый в качестве логина
        avatar (ImageField): Аватар
        is_staff (bool): Указывает, есть ли у пользователя права администратора
        is_active (bool): Указывает, является ли пользователь активным
        account_type (str): Тип пользователя (Продавец или Покупатель)

    Methods:
        full_name(): Возвращает полное имя пользователя, полученное путем объединения имени и фамилии
        __str__(): Возвращает строковое представление пользователя
    """

    first_name = models.CharField(verbose_name="Имя", max_length=25, null=True)
    last_name = models.CharField(verbose_name="Фамилия", max_length=25, null=True)
    email = models.EmailField(verbose_name="Email адрес", unique=True)
    avatar = models.ImageField(upload_to="avatars/", null=True, default='avatars/default.jpg')

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    account_type = models.CharField(max_length=6, choices=ACCOUNT_TYPE_CHOICES, default="BUYER")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = CustomUserManager()

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return self.full_name

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True

    @property
    def is_superuser(self):
        return self.is_staff
