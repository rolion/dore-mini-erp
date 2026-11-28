from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.test import TestCase

from modules.receivables.infrastructure.django.models import ObligationModel, PaymentModel
from modules.receivables.services import paid_totals


class PaidTotalsTests(TestCase):
    def payment(self, company, kind, number, amount, receipt):
        obligation, _ = ObligationModel.objects.get_or_create(
            company_id=company, source_kind=kind, source_number=number,
            defaults={'customer_id': uuid4(), 'customer_name': 'X'})
        PaymentModel.objects.create(
            company_id=company, obligation=obligation, receipt_number=receipt, amount=Decimal(amount),
            payment_method='CASH', payment_date=date(2026, 11, 1), idempotency_key=uuid4(), payload_hash='x',
            created_at='2026-11-01T10:00:00Z')

    def test_sums_by_number_kind_and_company(self):
        mine, theirs = uuid4(), uuid4()
        self.payment(mine, 'dental', 'ODO-1', '30.00', 'R1')
        self.payment(mine, 'dental', 'ODO-1', '20.50', 'R2')
        self.payment(mine, 'dental', 'ODO-2', '5.00', 'R3')
        self.payment(mine, 'quotation', 'ODO-1', '99.00', 'R4')
        self.payment(theirs, 'dental', 'ODO-1', '77.00', 'R5')
        self.assertEqual(paid_totals(mine, 'dental', ['ODO-1', 'ODO-2', 'ODO-3']),
                         {'ODO-1': Decimal('50.50'), 'ODO-2': Decimal('5.00')})
        self.assertEqual(paid_totals(mine, 'dental', []), {})
