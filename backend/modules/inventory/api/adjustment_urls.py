from django.urls import path

from .adjustment_views import StockAdjustmentBalanceView, StockAdjustmentDetailView, StockAdjustmentListCreateView

urlpatterns = [
    path('', StockAdjustmentListCreateView.as_view(), name='stock-adjustment-list'),
    path('balance/', StockAdjustmentBalanceView.as_view(), name='stock-adjustment-balance'),
    path('<uuid:adjustment_id>/', StockAdjustmentDetailView.as_view(), name='stock-adjustment-detail'),
]
