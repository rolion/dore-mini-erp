from django.urls import path

from .views import (
    ProductActivateView,
    ProductDeactivateView,
    ProductDetailView,
    ProductListCreateView,
)

urlpatterns = [
    path('', ProductListCreateView.as_view(), name='product-list'),
    path('<uuid:product_id>/', ProductDetailView.as_view(), name='product-detail'),
    path('<uuid:product_id>/activate/', ProductActivateView.as_view(), name='product-activate'),
    path('<uuid:product_id>/deactivate/', ProductDeactivateView.as_view(), name='product-deactivate'),
]
