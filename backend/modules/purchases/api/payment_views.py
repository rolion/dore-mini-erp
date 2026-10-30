from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.purchases.application.payment_commands import RegisterPayment
from modules.purchases.application.payment_queries import ListPayments
from modules.purchases.application.ports import Actor

from .pagination import SupplierPagination
from .payment_serializers import PaymentInputSerializer, payment_representation
from .purchase_views import REQUIRED_MODULES, _payments, _purchases, _run


def _actor(request) -> Actor:
    user = request.user
    return Actor(user.pk, user.get_full_name().strip() or user.get_username())


class PaymentListCreateView(APIView):
    required_modules = REQUIRED_MODULES

    def get(self, request, purchase_id):
        payments = _run(ListPayments(_purchases(request), _payments(request)).execute, purchase_id=purchase_id)
        paginator = SupplierPagination()
        page = paginator.paginate_queryset(payments, request, view=self)
        return paginator.get_paginated_response([payment_representation(p) for p in page])

    def post(self, request, purchase_id):
        serializer = PaymentInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        payment, created = _run(
            RegisterPayment(_purchases(request), _payments(request)).execute, purchase_id=purchase_id,
            payment_id=data['payment_id'], amount=data.get('amount'), payment_method=data.get('payment_method'),
            payment_date=data.get('payment_date'), actor=_actor(request), today=timezone.localdate())
        return Response(payment_representation(payment),
                        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
