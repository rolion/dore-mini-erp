from django.urls import path

from .stock_views import OpeningCheckView, OpeningCreateView, StockDetailView, StockListView

urlpatterns = [
    path('', StockListView.as_view(), name='stock-list'),
    path('openings/', OpeningCreateView.as_view(), name='stock-opening'),
    path('<uuid:product_id>/<uuid:warehouse_id>/', StockDetailView.as_view(), name='stock-detail'),
    path('opening-check/', OpeningCheckView.as_view(), name='stock-opening-check'),
]
