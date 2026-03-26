from django.contrib import admin

from apps.shop.models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "seller", "name", "category", "price_current", "in_stock", "is_deleted")
    search_fields = ("name",)
    list_filter = ("seller", "category", "is_deleted",)