"""PB-ACC-004: regularización de pagos históricos (AC-01..AC-10; INV-01..INV-08)."""
import json
import tempfile
import threading
from datetime import date, datetime, timezone
from decimal import Decimal
from io import StringIO
from pathlib import Path
from uuid import uuid4

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import SimpleTestCase, TestCase, TransactionTestCase

from modules.accounting import services
from modules.accounting.domain.account import Account
from modules.accounting.domain.entry import Entry
from modules.accounting.domain.regularization import (
    CONFLICT, DESTINATION_DIFFERENCE, EXISTING, INVALID, MISSING, PENDING, REASON_NO_MAPPING, REASON_OUT_OF_RANGE,
    RegularizationInputError, SourcePayment, classify, parse_mapping,
)
from modules.accounting.infrastructure.django.models import EntryModel
from modules.accounting.infrastructure.django.repositories import DjangoAccountRepository
from modules.accounts.testing import make_company
from modules.receivables.infrastructure.django.models import ObligationModel
from modules.receivables.infrastructure.django.models import PaymentModel as ServicePayment
from modules.sales.infrastructure.django.models import OrderModel
from modules.sales.infrastructure.django.models import PaymentModel as OrderPayment

D = date(2026, 3, 10)


def sp(**kw):
    data = dict(origin_kind='PRODUCT', id=uuid4(), amount=Decimal('100.00'), method='CASH', payment_date=D,
                document_ref='ord-1')
    data.update(kw)
    return SourcePayment(**data)


def make_entry(account, payment, **kw):
    data = dict(id=uuid4(), account_id=account.id, currency='BOB', amount=payment.amount,
                payment_date=payment.payment_date, method=payment.method, origin_kind=payment.origin_kind,
                origin_id=payment.id, origin_document_ref=payment.document_ref)
    data.update(kw)
    return Entry(**data)


class MappingAndClassifyTests(SimpleTestCase):
    def setUp(self):
        self.caja, self.banco = Account.create('Caja', 'BOB'), Account.create('Banco', 'BOB')
        self.usd = Account.create('USD', 'USD')
        self.accounts = {a.id: a for a in (self.caja, self.banco, self.usd)}

    def raw(self, **overrides):
        data = {'CASH': [{'account_id': str(self.caja.id), 'to': '2026-01-31'},
                         {'account_id': str(self.banco.id), 'from': '2026-02-01'}]}
        data.update(overrides)
        return data

    def test_period_mapping_picks_account_by_effective_date(self):  # AC-03
        mapping = parse_mapping(self.raw(), self.accounts)
        self.assertEqual(mapping.resolve('CASH', date(2026, 1, 15))[0], self.caja.id)
        self.assertEqual(mapping.resolve('CASH', date(2026, 3, 1))[0], self.banco.id)

    def test_unmapped_method_or_date_is_pending_with_reason_never_default(self):  # AC-02, INV-03
        mapping = parse_mapping({'CASH': [{'account_id': str(self.caja.id), 'to': '2026-01-31'}]}, self.accounts)
        self.assertEqual(mapping.resolve('QR', D), (None, REASON_NO_MAPPING))
        self.assertEqual(mapping.resolve('CASH', D), (None, REASON_OUT_OF_RANGE))
        item = classify(sp(method='QR'), None, mapping)
        self.assertEqual((item.status, item.reason, item.account_id), (PENDING, REASON_NO_MAPPING, None))

    def test_invalid_mappings_are_rejected(self):  # AC-09
        bad = [
            {}, {'XXX': [{'account_id': str(self.caja.id)}]}, {'CASH': []},
            {'CASH': [{'account_id': str(uuid4())}]}, {'CASH': [{'account_id': str(self.usd.id)}]},
            {'CASH': [{'account_id': 'no'}]}, {'CASH': [{'account_id': str(self.caja.id), 'from': 'ayer'}]},
            {'CASH': [{'account_id': str(self.caja.id), 'from': '2026-05-01', 'to': '2026-01-01'}]},
            {'CASH': [{'account_id': str(self.caja.id)}, {'account_id': str(self.banco.id), 'from': '2026-02-01'}]},
        ]
        for raw in bad:
            with self.assertRaises(RegularizationInputError, msg=raw):
                parse_mapping(raw, self.accounts)

    def test_classification(self):  # AC-01, AC-07
        mapping = parse_mapping({'CASH': [{'account_id': str(self.caja.id)}]}, self.accounts)
        p = sp()
        self.assertEqual(classify(p, None, mapping).status, MISSING)
        self.assertEqual(classify(p, make_entry(self.caja, p), mapping).status, EXISTING)
        conflict = classify(p, make_entry(self.caja, p, amount=Decimal('90.00')), mapping)
        self.assertEqual((conflict.status, conflict.fields), (CONFLICT, ('amount',)))
        other = classify(p, make_entry(self.banco, p), mapping)
        self.assertEqual((other.status, other.fields), (DESTINATION_DIFFERENCE, ('account_id',)))
        self.assertEqual(classify(sp(amount=Decimal('0')), None, mapping).status, INVALID)
        other_doc = classify(p, make_entry(self.caja, p, origin_document_ref='otro'), mapping)  # REV-01
        self.assertEqual((other_doc.status, other_doc.fields), (CONFLICT, ('origin_document_ref',)))

    def test_existing_without_mapping_is_not_flagged_for_destination(self):
        p = sp()
        self.assertEqual(classify(p, make_entry(self.caja, p), parse_mapping(
            {'QR': [{'account_id': str(self.caja.id)}]}, self.accounts)).status, EXISTING)

    def test_absent_fields_are_reported_not_invented(self):  # AC-05
        self.assertEqual(sp().absent_fields, ('author',))
        full = sp(origin_kind='SERVICE', recorded_by=3, recorded_by_name='Ana', receipt_number='CB-000001')
        self.assertEqual(full.absent_fields, ())


class RegularizeBase:
    def setUp(self):
        self.company, self.other = make_company('A'), make_company('B')
        self.accounts = DjangoAccountRepository(self.company.id)
        self.caja = self.accounts.save(Account.create('Caja', 'BOB'))
        self.banco = self.accounts.save(Account.create('Banco', 'BOB'))
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def mapping_file(self, data=None):
        data = data or {m: [{'account_id': str(self.caja.id)}] for m in ('CASH', 'QR', 'BANK_TRANSFER', 'CARD', 'OTHER')}
        path = Path(self.tmp.name) / 'map.json'
        path.write_text(json.dumps(data), encoding='utf-8')
        return str(path)

    def order_payment(self, company=None, status='DELIVERED', amount='100.00', method='CASH', day=D, reference=''):
        order = OrderModel.objects.create(company_id=(company or self.company).id, status=status, sales_channel='STORE',
                                          order_date=day, payment_status='paid')
        return OrderPayment.objects.create(order=order, amount=Decimal(amount), payment_method=method,
                                           payment_date=day, reference=reference)

    def service_payment(self, company=None, number='PF-1', receipt='CB-000001', amount='50.00', method='QR', day=D):
        company = company or self.company
        obligation = ObligationModel.objects.create(company_id=company.id, source_kind='quotation',
                                                    source_number=number, customer_id=uuid4(), customer_name='Cli')
        return ServicePayment.objects.create(
            company_id=company.id, obligation=obligation, receipt_number=receipt, amount=Decimal(amount),
            payment_method=method, payment_date=day, reference='ref-xyz', recorded_by=9, recorded_by_name='Beto',
            idempotency_key=uuid4(), payload_hash='h', created_at=datetime(2026, 3, 10, tzinfo=timezone.utc))

    def run_command(self, *args, company=None, **kw):
        out = StringIO()
        call_command('regularize_ledger', '--company', str((company or self.company).id), *args, stdout=out, **kw)
        return out.getvalue()

    def summary(self, *args, **kw):
        return json.loads(self.run_command('--json', *args, **kw))

    def count(self, kind=None, company=None):
        rows = EntryModel.objects.filter(company_id=(company or self.company).id)
        return rows.filter(origin_kind=kind).count() if kind else rows.count()

    def counts(self, summary, status):
        return sum(g['count'] for g in summary['groups'] if g['status'] == status)


class RegularizeCommandTests(RegularizeBase, TestCase):
    def dataset(self):
        missing = self.order_payment(amount='100.00')
        existing = self.order_payment(amount='40.00', method='QR')
        EntryModel.objects.create(company_id=self.company.id, account_id=self.caja.id, currency='BOB',
                                  amount=Decimal('40.00'), payment_date=D, payment_method='QR',
                                  origin_kind='PRODUCT', origin_id=existing.id,
                                  origin_document_ref=str(existing.order_id))
        cancelled = self.order_payment(status='CANCELLED', amount='25.00')
        service = self.service_payment()
        return missing, existing, cancelled, service

    def test_preview_does_not_write_and_apply_creates_only_eligible_missing(self):  # AC-01
        missing, existing, cancelled, service = self.dataset()
        before = self.count()
        preview = self.summary('--mapping', self.mapping_file())
        self.assertEqual(self.count(), before)
        self.assertEqual((preview['mode'], self.counts(preview, 'missing'), self.counts(preview, 'existing')),
                         ('preview', 3, 1))
        self.run_command('--apply', '--executed-by', 'Admin', '--mapping', self.mapping_file())
        self.assertEqual(self.count(), before + 3)
        ids = set(EntryModel.objects.values_list('origin_id', flat=True))
        self.assertTrue({missing.id, cancelled.id, service.id} <= ids)

    def test_unmapped_method_stays_pending_without_default_account(self):  # AC-02
        self.order_payment(method='CARD')
        mapping = self.mapping_file({'CASH': [{'account_id': str(self.caja.id)}]})
        result = self.summary('--apply', '--executed-by', 'Admin', '--mapping', mapping)
        self.assertEqual((self.counts(result, 'pending'), self.count()), (1, 0))
        self.assertEqual(result['details'][0]['reason'], REASON_NO_MAPPING)

    def test_period_mapping_sends_payments_to_different_accounts(self):  # AC-03
        old = self.order_payment(day=date(2026, 1, 5))
        new = self.order_payment(day=date(2026, 3, 5))
        mapping = self.mapping_file({'CASH': [{'account_id': str(self.caja.id), 'to': '2026-01-31'},
                                              {'account_id': str(self.banco.id), 'from': '2026-02-01'}]})
        self.run_command('--apply', '--executed-by', 'Admin', '--mapping', mapping)
        self.assertEqual(EntryModel.objects.get(origin_id=old.id).account_id, self.caja.id)
        self.assertEqual(EntryModel.objects.get(origin_id=new.id).account_id, self.banco.id)

    def test_second_run_creates_nothing(self):  # AC-04
        self.dataset()
        args = ('--apply', '--executed-by', 'Admin', '--mapping', self.mapping_file())
        self.run_command(*args)
        total = self.count()
        second = self.summary(*args)
        self.assertEqual((self.count(), self.counts(second, 'created'), self.counts(second, 'missing')), (total, 0, 0))

    def test_original_data_is_kept_and_regularization_recorded_apart(self):  # AC-05
        order = self.order_payment(reference='nota')
        service = self.service_payment()
        self.run_command('--apply', '--executed-by', 'Admin', '--mapping', self.mapping_file())
        product = EntryModel.objects.get(origin_id=order.id)
        self.assertEqual((product.payment_date, product.amount, product.payment_method, product.origin_document_ref),
                         (D, Decimal('100.00'), 'CASH', str(order.order_id)))
        self.assertEqual((product.recorded_by, product.recorded_by_name), (None, ''))
        svc = EntryModel.objects.get(origin_id=service.id)
        self.assertEqual((svc.receipt_number, svc.recorded_by, svc.recorded_by_name, svc.origin_document_ref),
                         ('CB-000001', 9, 'Beto', 'PF-1'))
        for row in (product, svc):
            self.assertEqual(row.regularized_by_name, 'Admin')
            self.assertIsNotNone(row.regularized_at)

    def test_regular_entries_have_no_regularization_stamp(self):  # AC-05
        account = self.caja
        result = services.record_entry(self.company.id, services.EntryInput(
            account_id=account.id, currency='BOB', amount=Decimal('5.00'), payment_date=D, method='CASH',
            origin_kind='PRODUCT', origin_id=uuid4()))
        row = EntryModel.objects.get(pk=result.entry.id)
        self.assertEqual((row.regularized_at, row.regularized_by_name), (None, ''))

    def test_payments_balances_unchanged_and_other_company_untouched(self):  # AC-06
        payment = self.order_payment()
        foreign = self.order_payment(company=self.other)
        before = (list(OrderPayment.objects.values_list('id', 'amount', 'payment_method')),
                  list(OrderModel.objects.values_list('id', 'paid_total', 'status')))
        self.run_command('--apply', '--executed-by', 'Admin', '--mapping', self.mapping_file())
        after = (list(OrderPayment.objects.values_list('id', 'amount', 'payment_method')),
                 list(OrderModel.objects.values_list('id', 'paid_total', 'status')))
        self.assertEqual(before, after)
        self.assertEqual((self.count(), self.count(company=self.other)), (1, 0))
        self.assertFalse(EntryModel.objects.filter(origin_id=foreign.id).exists())
        self.assertTrue(EntryModel.objects.filter(origin_id=payment.id).exists())

    def test_existing_entry_with_other_amount_is_conflict_and_kept(self):  # AC-07
        payment = self.order_payment(amount='100.00')
        entry = EntryModel.objects.create(company_id=self.company.id, account_id=self.caja.id, currency='BOB',
                                          amount=Decimal('90.00'), payment_date=D, payment_method='CASH',
                                          origin_kind='PRODUCT', origin_id=payment.id,
                                  origin_document_ref=str(payment.order_id))
        result = self.summary('--apply', '--executed-by', 'Admin', '--mapping', self.mapping_file())
        self.assertEqual(self.counts(result, 'conflict'), 1)
        self.assertEqual(result['details'][0]['fields'], ['amount'])
        entry.refresh_from_db()
        self.assertEqual((entry.amount, self.count()), (Decimal('90.00'), 1))

    def test_existing_entry_in_other_account_is_destination_difference_and_kept(self):  # AC-07
        payment = self.order_payment()
        entry = EntryModel.objects.create(company_id=self.company.id, account_id=self.banco.id, currency='BOB',
                                          amount=Decimal('100.00'), payment_date=D, payment_method='CASH',
                                          origin_kind='PRODUCT', origin_id=payment.id,
                                  origin_document_ref=str(payment.order_id))
        result = self.summary('--apply', '--executed-by', 'Admin', '--mapping', self.mapping_file())
        self.assertEqual(self.counts(result, 'destination_difference'), 1)
        entry.refresh_from_db()
        self.assertEqual(entry.account_id, self.banco.id)

    def test_report_groups_by_origin_account_currency_and_period_filter(self):  # AC-08
        self.order_payment(amount='10.00', day=date(2026, 1, 5))
        self.order_payment(amount='20.00', day=date(2026, 3, 5))
        self.service_payment(day=date(2026, 3, 5))
        result = self.summary('--mapping', self.mapping_file(), '--from', '2026-03-01', '--to', '2026-03-31')
        groups = {(g['origin'], g['status']): g for g in result['groups']}
        self.assertEqual(groups[('PRODUCT', 'missing')]['amount'], '20.00')
        self.assertEqual((groups[('SERVICE', 'missing')]['account'], groups[('SERVICE', 'missing')]['currency']),
                         ('Caja', 'BOB'))
        self.assertEqual(result['absent_fields'], {'author': 1})
        text = self.run_command('--mapping', self.mapping_file())
        self.assertIn('PREVISUALIZACIÓN', text)
        self.assertIn('no saldo bancario', text)

    def test_usage_errors_write_nothing(self):  # AC-09
        self.order_payment()
        mapping = self.mapping_file()
        cases = [
            ('--apply', '--mapping', mapping),
            ('--apply', '--executed-by', 'Admin'),
            ('--mapping', self.mapping_file({'CASH': [{'account_id': str(uuid4())}]})),
            ('--mapping', mapping, '--from', '2026-05-01', '--to', '2026-01-01'),
            ('--mapping', mapping, '--from', 'ayer'),
        ]
        for args in cases:
            with self.assertRaises(CommandError, msg=args):
                self.run_command(*args)
        with self.assertRaises(CommandError):  # empresa inexistente: ninguna cuenta del mapeo le pertenece
            self.run_command('--mapping', mapping, company=type('C', (), {'id': uuid4()})())
        self.assertEqual(self.count(), 0)

    def test_one_failure_does_not_stop_the_others_and_leaves_no_partial_entry(self):  # AC-10
        from modules.accounting.application.regularize import LedgerRejected, RegularizeLedger
        from modules.accounting.infrastructure.adapters import (
            DjangoRegularizationLedger, ReceivablesPaymentSource, SalesPaymentSource,
        )

        class RejectingLedger(DjangoRegularizationLedger):
            def create(self, company_id, item, regularized_at, executed_by):
                if item.payment.amount == Decimal('20.00'):
                    raise LedgerRejected('rechazada')
                return super().create(company_id, item, regularized_at, executed_by)

        good = self.order_payment(amount='10.00')
        self.order_payment(amount='20.00')
        mapping = parse_mapping({'CASH': [{'account_id': str(self.caja.id)}]}, self.accounts.by_id())
        use_case = RegularizeLedger({'PRODUCT': SalesPaymentSource(), 'SERVICE': ReceivablesPaymentSource()},
                                    RejectingLedger())
        report = use_case.apply(self.company.id, None, None, mapping, 'Admin', datetime.now(timezone.utc))
        self.assertEqual(sorted(i.outcome for i in report.items), ['created', 'failed'])
        self.assertEqual(list(EntryModel.objects.values_list('origin_id', flat=True)), [good.id])


class RegularizeConcurrencyTests(RegularizeBase, TransactionTestCase):
    def test_concurrent_runs_do_not_duplicate(self):  # AC-04
        payments = [self.order_payment(amount=f'{n}.00') for n in range(1, 6)]
        mapping = self.mapping_file()
        errors = []

        def run():
            try:
                self.run_command('--apply', '--executed-by', 'Admin', '--mapping', mapping)
            except CommandError as exc:
                errors.append(str(exc))
            finally:
                connection.close()

        threads = [threading.Thread(target=run) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(EntryModel.objects.filter(company_id=self.company.id).count(), len(payments))
        self.assertTrue(all('en curso' in e for e in errors))

    def test_entry_created_meanwhile_by_a_new_payment_counts_as_existing(self):  # EDGE-04
        from modules.accounting.application.regularize import RegularizeLedger
        from modules.accounting.domain.regularization import parse_mapping as parse
        from modules.accounting.infrastructure.adapters import (
            DjangoRegularizationLedger, ReceivablesPaymentSource, SalesPaymentSource,
        )
        payment = self.order_payment()
        ledger = DjangoRegularizationLedger()
        original = ledger.entries_by_origin

        def stale(company_id, kind, ids):
            found = original(company_id, kind, ids)
            if kind == 'PRODUCT':  # el cobro nuevo crea la entrada después de leer el libro
                EntryModel.objects.create(company_id=company_id, account_id=self.caja.id, currency='BOB',
                                          amount=payment.amount, payment_date=D, payment_method='CASH',
                                          origin_kind='PRODUCT', origin_id=payment.id,
                                          origin_document_ref=str(payment.order_id))
            return found

        ledger.entries_by_origin = stale
        use_case = RegularizeLedger({'PRODUCT': SalesPaymentSource(), 'SERVICE': ReceivablesPaymentSource()}, ledger)
        mapping = parse({'CASH': [{'account_id': str(self.caja.id)}]}, self.accounts.by_id())
        report = use_case.apply(self.company.id, None, None, mapping, 'Admin', datetime.now(timezone.utc))
        self.assertEqual([i.outcome for i in report.items], ['already_existed'])
        self.assertEqual(self.count(), 1)
