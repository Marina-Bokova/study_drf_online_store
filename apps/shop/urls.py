from django.urls import path

from apps.shop.views import CartView, CategoriesView, ProductView, ProductsByCategoryView, ProductsBySellerView, ProductsView

urlpatterns = [
    path("cart/", CartView.as_view()),
    path("categories/", CategoriesView.as_view()),
    path("categories/<slug:slug>/", ProductsByCategoryView.as_view()),
    path("sellers/<slug:slug>/", ProductsBySellerView.as_view()),
    path("products/", ProductsView.as_view()),
    path("products/<slug:slug>/", ProductView.as_view()),
]
