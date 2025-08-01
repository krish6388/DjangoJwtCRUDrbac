from django.urls import path
from .views import (
    ProductListCreateView,
    ProductDetailView,
    OrderListCreateView,
    # CategoryListView,
    CategoryListCreateView,
    CategoryDetailView
)


urlpatterns = [
    path('products/', ProductListCreateView.as_view(), name='product-list-create'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
    path('orders/', OrderListCreateView.as_view(), name='order-list-create'),
    # path('categories/', CategoryListView.as_view(), name='category-list'),
    path('categories/', CategoryListCreateView.as_view(), name='category-list-create'),
    path('categories/<int:pk>/', CategoryDetailView.as_view(), name='category-detail'),
]
