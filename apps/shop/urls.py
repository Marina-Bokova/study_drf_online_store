from django.urls import path

from apps.shop.views import CategoriesView

urlpatterns = [
    path("categories/", CategoriesView.as_view()),
]