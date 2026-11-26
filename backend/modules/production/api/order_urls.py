from django.urls import path

from .order_views import OrderDetailView, OrderListCreateView, OrderRefrigerateView, OrderStartView, OrderWarehousesView

urlpatterns = [
    path('', OrderListCreateView.as_view(), name='production-order-list'),
    path('warehouses/', OrderWarehousesView.as_view(), name='production-order-warehouses'),
    path('<uuid:order_id>/', OrderDetailView.as_view(), name='production-order-detail'),
    path('<uuid:order_id>/start/', OrderStartView.as_view(), name='production-order-start'),
    path('<uuid:order_id>/refrigerate/', OrderRefrigerateView.as_view(), name='production-order-refrigerate'),
]
