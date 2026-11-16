"""CONT-07 Etapa 1: diagnóstico de transición a partida doble (AC-01..AC-06; INV-01..INV-06)."""
import json
from datetime import date
from decimal import Decimal
from io import StringIO
from pathlib import Path
from uuid import uuid4

from django.apps import apps
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase

from modules.accounting.domain.transition import (
    ACCOUNT_WITHOUT_CODE, AMOUNT_DIFFERS, BEFORE_CUTOFF, CONVERTIBLE, HISTORICAL, NO_COUNTERPART_RULE, NO_CUTOFF,
    NO_EQUITY_ACCOUNT, PENDING, SOURCE_MISSING, SOURCE_UNVERIFIABLE, EntryFact, SourceFact, TransitionMapping,
    TransitionMappingError, classify_entry, classify_opening, parse_transition_mapping,
)
from modules.accounting.domain.account import Account
from modules.accounting.infrastructure.django.models import AccountModel, EntryModel, SettingsModel
from modules.accounting.infrastructure.django.repositories import DjangoAccountRepository
from modules.accounting.tests.test_regularization import D, RegularizeBase

CUTOFF = date(2026, 3, 1)
ACCOUNT = uuid4()


def fact(**kw):
    data = dict(id=uuid4(), origin_kind='PRODUCT', origin_id=uuid4(), operation='RECORD', direction='INCOME',
                amount=Decimal('100.00'), currency='BOB', payment_date=D, account_id=ACCOUNT)
    data.update(kw)
    return EntryFact(**data)


FULL = TransitionMapping({ACCOUNT: '101'}, {'PRODUCT': '401'}, '301')


class ClassifyTests(SimpleTestCase):
    def verdict(self, entry=None, source=SourceFact(Decimal('100.00')), verifiable=True, cutoff=CUTOFF, mapping=FULL):
        return classify_entry(entry or fact(), source, verifiable, cutoff, {ACCOUNT}, mapping)

    def test_without_rules_nothing_is_convertible(self):  # AC-02
        self.assertEqual(self.verdict(mapping=TransitionMapping()).reason, ACCOUNT_WITHOUT_CODE)
        only_codes = TransitionMapping({ACCOUNT: '101'})
        self.assertEqual((self.verdict(mapping=only_codes).state, self.verdict(mapping=only_codes).reason),
                         (PENDING, NO_COUNTERPART_RULE))

    def test_convertible_with_explicit_rules(self):  # AC-02
        self.assertEqual(self.verdict().state, CONVERTIBLE)

    def test_no_cutoff_blocks_and_before_cutoff_is_history(self):  # INV-04
        self.assertEqual((self.verdict(cutoff=None).state, self.verdict(cutoff=None).reason), (PENDING, NO_CUTOFF))
        old = self.verdict(fact(payment_date=date(2026, 2, 28)))
        self.assertEqual((old.state, old.reason), (HISTORICAL, BEFORE_CUTOFF))

    def test_source_checks(self):  # INV-03, INV-05
        self.assertEqual(self.verdict(source=None).reason, SOURCE_MISSING)
        self.assertEqual(self.verdict(source=SourceFact(Decimal('99.00'))).reason, AMOUNT_DIFFERS)
        self.assertEqual(self.verdict(verifiable=False).reason, SOURCE_UNVERIFIABLE)
        self.assertEqual(classify_entry(fact(), SourceFact(Decimal('100.00')), True, CUTOFF, set(), FULL).reason,
                         'empresa_inconsistente')
        self.assertEqual(self.verdict(fact(currency='USD')).reason, 'moneda_distinta')

    def test_opening_balance(self):  # AC-04
        self.assertIsNone(classify_opening(Decimal('0'), ACCOUNT, CUTOFF, FULL))
        self.assertEqual(classify_opening(Decimal('10'), ACCOUNT, CUTOFF, FULL).state, CONVERTIBLE)
        self.assertEqual(classify_opening(Decimal('10'), ACCOUNT, None, FULL).reason, NO_CUTOFF)
        self.assertEqual(classify_opening(Decimal('10'), ACCOUNT, CUTOFF, TransitionMapping({ACCOUNT: '101'})).reason,
                         NO_EQUITY_ACCOUNT)


class ParseMappingTests(SimpleTestCase):
    def test_valid(self):  # AC-03
        mapping = parse_transition_mapping({'money_accounts': {str(ACCOUNT): '101'}, 'counterparts': {'PRODUCT': '401'},
                                            'opening_equity': '301'}, {ACCOUNT})
        self.assertEqual(mapping, FULL)

    def test_invalid_is_rejected_with_messages(self):  # AC-03
        for raw in ({'money_accounts': {str(uuid4()): '101'}},  # cuenta de otra empresa
                    {'money_accounts': {str(ACCOUNT): ''}},
                    {'counterparts': {'XX': '401'}},
                    {'money_accounts': {str(ACCOUNT): '101'}, 'counterparts': {'PRODUCT': '101'}},
                    {'otra': 1}, []):
            with self.assertRaises(TransitionMappingError, msg=raw):
                parse_transition_mapping(raw, {ACCOUNT})


class DiagnoseCommandTests(RegularizeBase, TestCase):
    def run_diag(self, *args, company=None):
        out = StringIO()
        call_command('diagnose_ledger_transition', '--company', str((company or self.company).id), '--json', *args,
                     stdout=out)
        return json.loads(out.getvalue())['companies'][0]

    def entry(self, payment, company=None, account=None, **kw):
        data = dict(company_id=(company or self.company).id, account_id=(account or self.caja).id, currency='BOB',
                    amount=payment.amount, payment_date=payment.payment_date, payment_method='CASH',
                    origin_kind='PRODUCT', origin_id=payment.id)
        data.update(kw)
        return EntryModel.objects.create(**data)

    def seed(self):
        SettingsModel.objects.create(company_id=self.company.id, cutoff_date=date(2026, 3, 1))
        ok = self.order_payment(amount='100.00')
        old = self.order_payment(amount='40.00', day=date(2026, 2, 1))
        service = self.service_payment(amount='50.00', day=date(2026, 3, 12))
        self.order_payment(amount='25.00')  # sin entrada
        self.entry(ok)
        self.entry(old)
        self.entry(service, origin_kind='SERVICE', payment_method='QR')
        EntryModel.objects.create(company_id=self.company.id, account_id=self.caja.id, currency='BOB',
                                  amount=Decimal('9.00'), payment_date=D, payment_method='CASH',
                                  origin_kind='PRODUCT', origin_id=uuid4())  # huérfana
        AccountModel.objects.filter(id=self.banco.id).update(opening_balance=Decimal('500.50'))
        return ok

    def tables(self):
        prefixes = ('accounting_', 'sales_payment', 'receivables_payment', 'expenses_expense', 'purchases_payment')
        return {m._meta.db_table: m.objects.count() for m in apps.get_models() if m._meta.db_table.startswith(prefixes)}

    def test_inventory_matches_data(self):  # AC-01
        self.seed()
        report = self.run_diag()
        self.assertEqual(report['accounts'], {'total': 2, 'active': 2, 'with_kind': 0, 'without_kind': 2,
                                              'with_entries': 1, 'opening_total': '500.50'})
        self.assertEqual((report['entries']['total'], report['entries']['amount']), (4, '199.00'))
        self.assertEqual(report['entries']['by_shape']['INCOME/RECORD/PRODUCT'], {'count': 3, 'amount': '149.00'})
        self.assertEqual(report['source_without_entry'], {'PRODUCT/sin_entrada': {'count': 1, 'amount': '25.00'}})

    def test_without_rules_every_post_cutoff_entry_is_pending_and_reported(self):  # AC-02 (aceptación 4)
        self.seed()
        report = self.run_diag()
        self.assertEqual(report['states'][CONVERTIBLE]['count'], 0)
        self.assertEqual(report['states'][HISTORICAL]['count'], 1)
        self.assertEqual(report['states'][PENDING]['count'], 3)
        self.assertEqual(report['reasons'], {'anterior_al_corte': 1, 'cuenta_sin_codigo': 2, 'origen_inexistente': 1})
        self.assertEqual(len(report['details']), 3)

    def test_mapping_makes_covered_entries_convertible(self):  # AC-03
        self.seed()
        path = Path(self.tmp.name) / 'transition.json'
        path.write_text(json.dumps({'money_accounts': {str(self.caja.id): '101'},
                                    'counterparts': {'PRODUCT': '401', 'SERVICE': '402'}, 'opening_equity': '301'}),
                        encoding='utf-8')
        report = self.run_diag('--mapping', str(path))
        self.assertEqual(report['states'][CONVERTIBLE]['count'], 2)
        self.assertEqual(report['reasons'], {'anterior_al_corte': 1, 'origen_inexistente': 1})
        self.assertEqual(report['openings'], [{'account_id': str(self.banco.id), 'amount': '500.50',
                                               'state': PENDING, 'reason': ACCOUNT_WITHOUT_CODE}])

    def test_invalid_mapping_is_rejected(self):  # AC-03
        self.seed()
        path = Path(self.tmp.name) / 'bad.json'
        path.write_text(json.dumps({'money_accounts': {str(uuid4()): '101'}}), encoding='utf-8')
        with self.assertRaises(CommandError):
            self.run_diag('--mapping', str(path))
        path.write_text('{"counterparts": {"PRODUCT": "1", "PRODUCT": "2"}}', encoding='utf-8')
        with self.assertRaises(CommandError):
            self.run_diag('--mapping', str(path))
        with self.assertRaises(CommandError):  # el mapeo exige --company
            call_command('diagnose_ledger_transition', '--mapping', str(path), stdout=StringIO())

    def test_company_without_cutoff_is_blocked(self):  # AC-04
        payment = self.order_payment()
        self.entry(payment)
        report = self.run_diag()
        self.assertTrue(report['blocked_without_cutoff'])
        self.assertEqual(report['reasons'], {'sin_corte': 1})

    def test_never_writes_and_is_deterministic(self):  # AC-05, INV-01, INV-06
        self.seed()
        before = self.tables()
        first, second = self.run_diag(), self.run_diag()
        self.assertEqual(first, second)
        self.assertEqual(self.tables(), before)

    def test_company_isolation(self):  # AC-06, INV-02
        self.seed()
        other_account = DjangoAccountRepository(self.other.id).save(Account.create('Caja B', 'BOB'))
        payment = self.order_payment(company=self.other, amount='7.00')
        self.entry(payment, company=self.other, account=other_account)
        mine, theirs = self.run_diag(), self.run_diag(company=self.other)
        self.assertEqual(mine['entries']['total'], 4)
        self.assertEqual((theirs['entries']['total'], theirs['entries']['amount']), (1, '7.00'))
        self.assertEqual(theirs['accounts']['total'], 1)
        out = StringIO()
        call_command('diagnose_ledger_transition', '--json', stdout=out)  # sin --company: cada empresa lo suyo
        by_company = {c['company_id']: c for c in json.loads(out.getvalue())['companies']}
        self.assertEqual(by_company[str(self.company.id)]['entries']['total'], 4)
        self.assertEqual(by_company[str(self.other.id)]['entries']['total'], 1)

    def test_text_output(self):
        self.seed()
        out = StringIO()
        call_command('diagnose_ledger_transition', '--company', str(self.company.id), stdout=out)
        self.assertIn('pendiente: 3', out.getvalue())
        self.assertIn('Pagos de origen sin entrada PRODUCT/sin_entrada: 1', out.getvalue())
