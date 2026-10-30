from django.urls import path

from .movement_views import StockMovementDetailView, StockMovementListView, StockMovementReverseView

urlpatterns = [
    path('', StockMovementListView.as_view(), name='stock-movement-list'),
    path('<uuid:movement_id>/', StockMovementDetailView.as_view(), name='stock-movement-detail'),
    path('<uuid:movement_id>/reverse/', StockMovementReverseView.as_view(), name='stock-movement-reverse'),
]
