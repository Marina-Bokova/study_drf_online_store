from django.urls import path

from apps.sellers.views import SellersView, SellerProductsView

urlpatterns = [
    path("", SellersView.as_view()),
    path("products/", SellerProductsView.as_view()),
]