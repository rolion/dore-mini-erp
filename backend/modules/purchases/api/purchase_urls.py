from django.urls import path

from .purchase_views import PurchaseCancelView, PurchaseConfirmView, PurchaseDetailView, PurchaseListCreateView

urlpatterns = [
    path('', PurchaseListCreateView.as_view(), name='purchase-list'),
    path('<uuid:purchase_id>/', PurchaseDetailView.as_view(), name='purchase-detail'),
    path('<uuid:purchase_id>/confirm/', PurchaseConfirmView.as_view(), name='purchase-confirm'),
    path('<uuid:purchase_id>/cancel/', PurchaseCancelView.as_view(), name='purchase-cancel'),
]
