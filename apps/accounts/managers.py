from django.contrib.auth.base_user import BaseUserManager
from django.core.validators import validate_email
from django.core.exceptions import ValidationError


class CustomUserManager(BaseUserManager):

    def email_validator(self, email):
        try:
            validate_email(email)
        except ValidationError:
            raise ValueError("Необходимо указать корректный адрес электронной почты")

    def validate_user(self, first_name, last_name, email, password):
        if not first_name:
            raise ValueError("Необходимо указать имя пользователя")

        if not last_name:
            raise ValueError("Необходимо указать фамилию пользователя")

        if email:
            email = self.normalize_email(email)
            self.email_validator(email)
        else:
            raise ValueError("Необходимо указать адрес электронной почты")

        if not password:
            raise ValueError("Необходимо задать пароль для входа в профиль")

    def create_user(self, first_name, last_name, email, password, **extra_fields):
        self.validate_user(first_name, last_name, email, password)

        user = self.model(
            first_name=first_name, last_name=last_name, email=email, **extra_fields
        )

        user.set_password(password)
        user.save()
        return user

    def validate_superuser(self, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Для роли администратора необходимо указать is_staff=True')
        return extra_fields

    def create_superuser(self, first_name, last_name, email, password, **extra_fields):
        extra_fields = self.validate_superuser(**extra_fields)
        user = self.create_user(first_name, last_name, email, password, **extra_fields)
        return user
