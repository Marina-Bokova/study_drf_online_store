from django.contrib import admin

from apps.sellers.models import Seller


@admin.register(Seller)
class SellerAdmin(admin.ModelAdmin):
    list_display = ("user", "business_name", "slug", "is_approved")
    search_fields = ("business_name",)
    list_filter = ("is_approved",)
