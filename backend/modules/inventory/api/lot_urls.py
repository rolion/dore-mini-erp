from django.urls import path

from .lot_views import LotDetailView, LotListView

urlpatterns = [
    path('', LotListView.as_view(), name='stock-lot-list'),
    path('<uuid:lot_id>/', LotDetailView.as_view(), name='stock-lot-detail'),
]
