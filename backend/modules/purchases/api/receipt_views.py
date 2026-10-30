from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.purchases.application.ports import Actor
from modules.purchases.application.receipt_commands import ReceiptLineInput, RegisterReception
from modules.purchases.application.receipt_queries import GetReceipt, GetReceptionForm, ListReceipts
from modules.purchases.infrastructure.adapters import ProductCatalogAdapter, StockEntryAdapter
from shared.tenancy import company_id_from

from .pagination import SupplierPagination
from .purchase_views import REQUIRED_MODULES, _purchases, _receipts, _run
from .receipt_serializers import (
    ReceiptInputSerializer,
    receipt_representation,
    receipt_summary,
    reception_form_representation,
)


def _stock(request) -> StockEntryAdapter:
    return StockEntryAdapter(company_id_from(request))


def _actor(request) -> Actor:
    user = request.user
    return Actor(user.pk, user.get_full_name().strip() or user.get_username())


class ReceptionFormView(APIView):
    required_modules = REQUIRED_MODULES

    def get(self, request, purchase_id):
        use_case = GetReceptionForm(_purchases(request), _receipts(request),
                                    ProductCatalogAdapter(company_id_from(request)), _stock(request))
        return Response(reception_form_representation(_run(use_case.execute, purchase_id=purchase_id)))


class ReceiptListCreateView(APIView):
    required_modules = REQUIRED_MODULES

    def get(self, request, purchase_id):
        receipts = _run(ListReceipts(_purchases(request), _receipts(request)).execute, purchase_id=purchase_id)
        paginator = SupplierPagination()
        page = paginator.paginate_queryset(receipts, request, view=self)
        return paginator.get_paginated_response([receipt_summary(r) for r in page])

    def post(self, request, purchase_id):
        serializer = ReceiptInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        use_case = RegisterReception(_purchases(request), _receipts(request),
                                     ProductCatalogAdapter(company_id_from(request)), _stock(request))
        receipt, created = _run(
            use_case.execute, purchase_id=purchase_id, receipt_id=data['receipt_id'],
            receipt_date=data.get('receipt_date'), warehouse_id=data.get('warehouse_id'), actor=_actor(request),
            today=timezone.localdate(),
            lines=[ReceiptLineInput(line['item_id'], line['quantity']) for line in data.get('lines', [])])
        detail = _run(GetReceipt(_purchases(request), _receipts(request), _stock(request)).execute,
                      purchase_id=purchase_id, receipt_id=receipt.id)
        return Response(receipt_representation(detail),
                        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class ReceiptDetailView(APIView):
    required_modules = REQUIRED_MODULES

    def get(self, request, purchase_id, receipt_id):
        use_case = GetReceipt(_purchases(request), _receipts(request), _stock(request))
        return Response(receipt_representation(
            _run(use_case.execute, purchase_id=purchase_id, receipt_id=receipt_id)))
