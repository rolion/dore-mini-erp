from django.urls import path

from .purchase_views import PurchaseCancelView, PurchaseConfirmView, PurchaseDetailView, PurchaseListCreateView
from .receipt_views import ReceiptDetailView, ReceiptListCreateView, ReceptionFormView

urlpatterns = [
    path('', PurchaseListCreateView.as_view(), name='purchase-list'),
    path('<uuid:purchase_id>/', PurchaseDetailView.as_view(), name='purchase-detail'),
    path('<uuid:purchase_id>/confirm/', PurchaseConfirmView.as_view(), name='purchase-confirm'),
    path('<uuid:purchase_id>/cancel/', PurchaseCancelView.as_view(), name='purchase-cancel'),
    path('<uuid:purchase_id>/reception-form/', ReceptionFormView.as_view(), name='purchase-reception-form'),
    path('<uuid:purchase_id>/receipts/', ReceiptListCreateView.as_view(), name='purchase-receipts'),
    path('<uuid:purchase_id>/receipts/<uuid:receipt_id>/', ReceiptDetailView.as_view(), name='purchase-receipt'),
]
