from django.urls import path

from .purchase_views import PurchaseDetailView, PurchaseListCreateView

urlpatterns = [
    path('', PurchaseListCreateView.as_view(), name='purchase-list'),
    path('<uuid:purchase_id>/', PurchaseDetailView.as_view(), name='purchase-detail'),
]
