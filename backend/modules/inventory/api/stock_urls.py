from django.urls import path

from .stock_views import OpeningCheckView, OpeningCreateView, StockListView

urlpatterns = [
    path('', StockListView.as_view(), name='stock-list'),
    path('openings/', OpeningCreateView.as_view(), name='stock-opening'),
    path('opening-check/', OpeningCheckView.as_view(), name='stock-opening-check'),
]
