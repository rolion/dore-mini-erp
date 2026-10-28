from django.urls import path

from .movement_views import StockMovementDetailView, StockMovementListView

urlpatterns = [
    path('', StockMovementListView.as_view(), name='stock-movement-list'),
    path('<uuid:movement_id>/', StockMovementDetailView.as_view(), name='stock-movement-detail'),
]
