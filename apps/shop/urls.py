from django.urls import path

from apps.shop.views import (
    CartView,
    CategoriesView,
    CheckoutView,
    ProductReviewsView,
    ProductView,
    ProductsByCategoryView,
    ProductsBySellerView,
    ProductsView,
    ReviewDetailView,
)

urlpatterns = [
    path("cart/", CartView.as_view()),
    path("checkout/", CheckoutView.as_view()),
    path("categories/", CategoriesView.as_view()),
    path("categories/<slug:slug>/", ProductsByCategoryView.as_view()),
    path("sellers/<slug:slug>/", ProductsBySellerView.as_view()),
    path("products/", ProductsView.as_view()),
    path("products/<slug:slug>/", ProductView.as_view()),
    path("products/<slug:slug>/reviews/", ProductReviewsView.as_view()),
    path("reviews/<uuid:id>/", ReviewDetailView.as_view()),
]
