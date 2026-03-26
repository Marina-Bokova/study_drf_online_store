from django.contrib import admin

from apps.accounts.models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "email", "account_type", "is_staff", "is_deleted")
    search_fields = ("first_name", "last_name", "email",)
    list_filter = ("account_type", "is_deleted",)