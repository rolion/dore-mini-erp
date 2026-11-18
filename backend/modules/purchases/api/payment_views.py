from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.purchases.application.payment_commands import RegisterPayment
from modules.purchases.application.payment_queries import ListPayments, PreviewPayment
from modules.purchases.application.ports import Actor
from modules.purchases.application.settings_commands import GetPaymentClassification, SetPaymentClassification
from modules.purchases.infrastructure.adapters import AccountingClassifications, PurchasePostingAdapter
from modules.purchases.infrastructure.django.settings_repository import DjangoPurchaseSettingsRepository
from shared.tenancy import company_id_from

from .pagination import SupplierPagination
from .payment_serializers import (
    PaymentClassificationInputSerializer,
    PaymentInputSerializer,
    PaymentPreviewQuerySerializer,
    payment_representation,
    preview_representation,
)
from .purchase_views import REQUIRED_MODULES, _payments, _purchases, _receipts, _run


def _actor(request) -> Actor:
    user = request.user
    return Actor(user.pk, user.get_full_name().strip() or user.get_username())


def _gateway(request) -> AccountingClassifications:
    return AccountingClassifications(company_id_from(request))


def _posting(request) -> PurchasePostingAdapter:
    return PurchasePostingAdapter(company_id_from(request))


def _settings(request) -> DjangoPurchaseSettingsRepository:
    return DjangoPurchaseSettingsRepository(company_id_from(request))


class PaymentListCreateView(APIView):
    required_modules = REQUIRED_MODULES

    def get(self, request, purchase_id):
        payments = _run(ListPayments(_purchases(request), _payments(request)).execute, purchase_id=purchase_id)
        paginator = SupplierPagination()
        page = paginator.paginate_queryset(payments, request, view=self)
        classifications = _gateway(request).describe({p.classification_id for p in page if p.classification_id})
        entries = _posting(request).payment_entries([p.id for p in page])
        return paginator.get_paginated_response(
            [payment_representation(p, classifications, entries.get(p.id, ())) for p in page])

    def post(self, request, purchase_id):
        serializer = PaymentInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        payment, created = _run(
            RegisterPayment(_purchases(request), _payments(request), _settings(request), _gateway(request),
                            _posting(request), _receipts(request)).execute, purchase_id=purchase_id,
            payment_id=data['payment_id'], amount=data.get('amount'), payment_method=data.get('payment_method'),
            payment_date=data.get('payment_date'), actor=_actor(request), today=timezone.localdate())
        classifications = _gateway(request).describe([payment.classification_id] if payment.classification_id else [])
        entries = _posting(request).payment_entries([payment.id])
        return Response(payment_representation(payment, classifications, entries.get(payment.id, ())),
                        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class PaymentPreviewView(APIView):
    """Asiento previsto de un pago (no escribe): reparto deuda/anticipo, líneas y faltantes."""

    required_modules = REQUIRED_MODULES

    def get(self, request, purchase_id):
        serializer = PaymentPreviewQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        preview = _run(
            PreviewPayment(_purchases(request), _payments(request), _receipts(request), _posting(request)).execute,
            purchase_id=purchase_id, amount=data.get('amount'), payment_method=data.get('payment_method'),
            payment_date=data.get('payment_date'), today=timezone.localdate())
        return Response(preview_representation(preview))


def _setting_response(info) -> Response:
    classification = None if info is None else {'id': info.id, 'name': info.name, 'active': info.active}
    return Response({'classification': classification})


class PaymentClassificationView(APIView):
    """Clasificación de egreso de los pagos a proveedores (configuración de Compras)."""

    required_modules = REQUIRED_MODULES

    def get(self, request):
        return _setting_response(GetPaymentClassification(_settings(request), _gateway(request)).execute())

    def put(self, request):
        serializer = PaymentClassificationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        info = _run(SetPaymentClassification(_settings(request), _gateway(request)).execute,
                    classification_id=serializer.validated_data['classification_id'])
        return _setting_response(info)
