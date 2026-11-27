from django.urls import path

from .purchase_views import PurchaseCancelView, PurchaseConfirmView, PurchaseDetailView, PurchaseListCreateView
from .purchase_report_views import (
    PaidPurchasesReportExportView,
    PaidPurchasesReportView,
    PayablePurchasesReportExportView,
    PayablePurchasesReportView,
)
from .payment_views import PaymentClassificationView, PaymentListCreateView, PaymentPreviewView
from .receipt_views import ReceiptDetailView, ReceiptListCreateView, ReceiptRevertView, ReceptionFormView

urlpatterns = [
    path('', PurchaseListCreateView.as_view(), name='purchase-list'),
    path('payment-classification/', PaymentClassificationView.as_view(), name='purchase-payment-classification'),
    path('paid-report/', PaidPurchasesReportView.as_view(), name='purchase-paid-report'),
    path('paid-report/export/<str:file_format>/', PaidPurchasesReportExportView.as_view(),
         name='purchase-paid-report-export'),
    path('payable-report/', PayablePurchasesReportView.as_view(), name='purchase-payable-report'),
    path('payable-report/export/<str:file_format>/', PayablePurchasesReportExportView.as_view(),
         name='purchase-payable-report-export'),
    path('<uuid:purchase_id>/', PurchaseDetailView.as_view(), name='purchase-detail'),
    path('<uuid:purchase_id>/confirm/', PurchaseConfirmView.as_view(), name='purchase-confirm'),
    path('<uuid:purchase_id>/cancel/', PurchaseCancelView.as_view(), name='purchase-cancel'),
    path('<uuid:purchase_id>/payments/', PaymentListCreateView.as_view(), name='purchase-payments'),
    path('<uuid:purchase_id>/payments/preview/', PaymentPreviewView.as_view(), name='purchase-payment-preview'),
    path('<uuid:purchase_id>/reception-form/', ReceptionFormView.as_view(), name='purchase-reception-form'),
    path('<uuid:purchase_id>/receipts/', ReceiptListCreateView.as_view(), name='purchase-receipts'),
    path('<uuid:purchase_id>/receipts/<uuid:receipt_id>/', ReceiptDetailView.as_view(), name='purchase-receipt'),
    path('<uuid:purchase_id>/receipts/<uuid:receipt_id>/revert/', ReceiptRevertView.as_view(),
         name='purchase-receipt-revert'),
]
