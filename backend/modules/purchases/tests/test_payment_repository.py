from datetime import date
from decimal import Decimal
from unittest import skipUnless
from uuid import uuid4

from django.db import IntegrityError, connection, transaction
from django.test import TestCase

from modules.purchases.domain.enums import PaymentMethod, PaymentRecordStatus
from modules.purchases.domain.exceptions import PaymentConflict
from modules.purchases.domain.payment import Payment
from modules.purchases.infrastructure.django.models import PaymentModel
from modules.purchases.infrastructure.django.payment_repository import DjangoPaymentRepository


def payment(purchase_id, amount='10.00', when=date(2026, 10, 30), status=PaymentRecordStatus.CONFIRMED):
    return Payment(id=uuid4(), purchase_id=purchase_id, amount=Decimal(amount), payment_method=PaymentMethod.CASH,
                   payment_date=when, user_id=uuid4(), user_name='Ana', status=status)


class PaymentRepositoryTests(TestCase):
    def setUp(self):
        self.company_id = uuid4()
        self.purchase_id = uuid4()
        self.repo = DjangoPaymentRepository(self.company_id)

    def test_round_trip(self):  # AC-01
        saved = self.repo.save(payment(self.purchase_id, '12.34'))
        self.assertIsNotNone(saved.created_at)
        loaded = self.repo.get(saved.id)
        self.assertEqual((loaded.amount, loaded.payment_method, loaded.status, loaded.user_name),
                         (Decimal('12.34'), PaymentMethod.CASH, PaymentRecordStatus.CONFIRMED, 'Ana'))

    def test_paid_total_sums_only_confirmed_payments(self):  # AC-02
        self.assertEqual(self.repo.paid_total(self.purchase_id), Decimal('0.00'))
        self.repo.save(payment(self.purchase_id, '10.00'))
        self.repo.save(payment(self.purchase_id, '5.50'))
        self.repo.save(payment(self.purchase_id, '99.00', status=PaymentRecordStatus.VOIDED))
        self.repo.save(payment(uuid4(), '7.00'))
        self.assertEqual(self.repo.paid_total(self.purchase_id), Decimal('15.50'))

    def test_list_is_ordered_by_date_desc(self):  # AC-10
        old = self.repo.save(payment(self.purchase_id, when=date(2026, 10, 1)))
        new = self.repo.save(payment(self.purchase_id, when=date(2026, 10, 20)))
        self.assertEqual([p.id for p in self.repo.list_for_purchase(self.purchase_id)], [new.id, old.id])

    def test_isolation_between_companies(self):  # AC-12
        saved = self.repo.save(payment(self.purchase_id))
        other = DjangoPaymentRepository(uuid4())
        self.assertIsNone(other.get(saved.id))
        self.assertEqual(other.list_for_purchase(self.purchase_id), [])
        self.assertEqual(other.paid_total(self.purchase_id), Decimal('0.00'))

    def test_duplicate_id_is_a_conflict_that_keeps_the_transaction_usable(self):  # AC-08
        saved = self.repo.save(payment(self.purchase_id))
        duplicate = payment(self.purchase_id)
        duplicate.id = saved.id
        with self.assertRaises(PaymentConflict):
            self.repo.save(duplicate)
        self.assertEqual(PaymentModel.objects.count(), 1)

    @skipUnless(connection.vendor in ('postgresql', 'sqlite'), 'Requiere soporte de CheckConstraint.')
    def test_database_rejects_non_positive_amounts(self):  # AC-14
        for bad in ('0.00', '-1.00'):
            with self.assertRaises(IntegrityError), transaction.atomic():
                PaymentModel.objects.create(company_id=self.company_id, purchase_id=self.purchase_id,
                                            amount=Decimal(bad), payment_method='CASH',
                                            payment_date=date(2026, 10, 30))
