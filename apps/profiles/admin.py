from django.contrib import admin

from apps.profiles.models import ShippingAddress, Order, OrderItem


@admin.register(ShippingAddress)
class ShippingAddressAdmin(admin.ModelAdmin):
    list_display = ("user", "full_name", "country", "city", "address")
    search_fields = ("full_name", "address",)
    list_filter = ("user", "country", "city",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("user", "tx_ref", "delivery_status", "payment_status")
    list_filter = ("user", "delivery_status", "payment_status",)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("user", "order", "product", "quantity")
    list_filter = ("user", "order", "product",)
