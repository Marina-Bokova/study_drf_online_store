import uuid

from django.db import models
from django.utils import timezone

from apps.common.managers import GetOrNoneManager, IsDeletedManager


class BaseModel(models.Model):
    """
    Базовая модель, включающая общие поля и методы для всех моделей

    Attributes:
        id (UUIDField): Уникальный идентификатор объекта.
        created_at (DateTimeField): Временная метка создания объекта.
        updated_at (DateTimeField): Временная метка последнего обновления объекта.
    """

    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = GetOrNoneManager()

    class Meta:
        ordering = ['-created_at', 'id']
        abstract = True


class IsDeletedModel(BaseModel):
    """
    Абстрактная модель, добавляющая к базовой модели функции мягкого удаления объекта

    Attributes:
        is_deleted (bool): Поле для указания, удален объект или нет.
        deleted_at (DateTimeField): Временная метка удаления объекта.

    Methods:
        delete(): Мягкое удаление объекта
        hard_delete(): Безвозвратное удаление объекта
    """

    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    objects = IsDeletedManager()

    def delete(self, *args, **kwargs):
        # Мягкое удаление is_deleted=True
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at"])

    def hard_delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)