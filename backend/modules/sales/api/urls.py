from django.urls import path

from .views import (
    OrderCancelView,
    OrderDeliverView,
    OrderDetailView,
    OrderDiscountView,
    OrderItemDetailView,
    OrderItemListView,
    OrderListCreateView,
    OrderPaymentView,
    OrderPrepareView,
    OrderReadyView,
)

# Los ids van como `str` y la vista los convierte: un id mal formado responde 404 `{detail}`, no una página HTML.
urlpatterns = [
    path('', OrderListCreateView.as_view(), name='order-list'),
    path('<str:order_id>/', OrderDetailView.as_view(), name='order-detail'),
    path('<str:order_id>/items/', OrderItemListView.as_view(), name='order-item-list'),
    path('<str:order_id>/items/<str:item_id>/', OrderItemDetailView.as_view(), name='order-item-detail'),
    path('<str:order_id>/discount/', OrderDiscountView.as_view(), name='order-discount'),
    path('<str:order_id>/prepare/', OrderPrepareView.as_view(), name='order-prepare'),
    path('<str:order_id>/ready/', OrderReadyView.as_view(), name='order-ready'),
    path('<str:order_id>/deliver/', OrderDeliverView.as_view(), name='order-deliver'),
    path('<str:order_id>/cancel/', OrderCancelView.as_view(), name='order-cancel'),
    path('<str:order_id>/payments/', OrderPaymentView.as_view(), name='order-payments'),
]
