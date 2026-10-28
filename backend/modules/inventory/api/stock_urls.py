from django.urls import path

from .stock_views import OpeningCheckView, OpeningCreateView, StockListView, StockMovementListView

urlpatterns = [
    path('', StockListView.as_view(), name='stock-list'),
    path('movements/', StockMovementListView.as_view(), name='stock-movements'),
    path('openings/', OpeningCreateView.as_view(), name='stock-opening'),
    path('opening-check/', OpeningCheckView.as_view(), name='stock-opening-check'),
]
