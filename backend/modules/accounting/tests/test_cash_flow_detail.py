"""CONT-14: detalle del flujo de dinero. AC-01..AC-08 del PLAN; INV-02..INV-05."""
from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.test import SimpleTestCase

from modules.accounting import services
from modules.accounting.domain.ledger_report import (
    INFLOW,
    TRANSFER_IN,
    TRANSFER_OUT,
    EntryMoneyLine,
    MoneyAccount,
    build_cash_flow,
    build_cash_flow_movements,
)
from modules.accounting.infrastructure.django.models import SettingsModel
from modules.accounting.infrastructure.django.repositories import DjangoAccountRepository
from modules.accounting.tests.journal_support import make_account, make_period, money_account
from modules.accounting.tests.test_api import AccountingApiBase
from modules.accounting.tests.test_entries_api import enable
from modules.modularity.infrastructure.django.models import CompanyModuleModel

D = Decimal
DAY = date(2026, 5, 10)
FROM, TO = date(2026, 5, 1), date(2026, 5, 31)
URL = '/api/accounting/cash-flow/'
MOVES = '/api/accounting/cash-flow/movements/'


class CashFlowDomainTests(SimpleTestCase):
    def setUp(self):
        self.cash, self.bank, self.third = uuid4(), uuid4(), uuid4()
        self.names = {self.cash: 'Caja', self.bank: 'Banco', self.third: 'Billetera'}
        self.accounts = [MoneyAccount(i, n) for i, n in self.names.items()]

    def kinds(self, lines):
        return sorted((self.names[m.account_id], m.kind, m.amount)
                      for m in build_cash_flow_movements(lines, self.names))

    def test_scenario_from_the_card_gives_727(self):  # AC-03
        lines = [EntryMoneyLine(uuid4(), self.cash, D('2477.00')), EntryMoneyLine(uuid4(), self.cash, D('-1750.00'))]
        flow = build_cash_flow(self.accounts, {}, lines)
        self.assertEqual((flow.opening, flow.inflow, flow.outflow, flow.net, flow.closing),
                         (0, D('2477.00'), D('1750.00'), D('727.00'), D('727.00')))

    def test_transfer_is_sent_from_cash_and_received_in_bank(self):  # AC-04
        entry = uuid4()
        lines = [EntryMoneyLine(entry, self.cash, D('-500.00')), EntryMoneyLine(entry, self.bank, D('500.00'))]
        self.assertEqual(self.kinds(lines), [('Banco', TRANSFER_IN, D('500.00')), ('Caja', TRANSFER_OUT, D('500.00'))])
        flow = build_cash_flow(self.accounts, {}, lines)
        by_name = {a.name: a for a in flow.accounts}
        self.assertEqual((flow.inflow, flow.outflow, flow.net, flow.transfers), (0, 0, 0, D('500.00')))
        self.assertEqual((by_name['Caja'].transfers_out, by_name['Banco'].transfers_in), (D('500.00'), D('500.00')))
        self.assertEqual((by_name['Caja'].closing, by_name['Banco'].closing), (D('-500.00'), D('500.00')))

    def test_pure_inflow_split_between_accounts(self):
        entry = uuid4()
        lines = [EntryMoneyLine(entry, self.cash, D('200.00')), EntryMoneyLine(entry, self.bank, D('300.00'))]
        self.assertEqual(self.kinds(lines), [('Banco', INFLOW, D('300.00')), ('Caja', INFLOW, D('200.00'))])

    def test_mixed_entry_splits_transfer_and_external_part(self):  # INV-04
        entry = uuid4()
        lines = [EntryMoneyLine(entry, self.cash, D('700.00')), EntryMoneyLine(entry, self.bank, D('-200.00'))]
        self.assertEqual(self.kinds(lines), [('Banco', TRANSFER_OUT, D('200.00')), ('Caja', INFLOW, D('500.00')),
                                             ('Caja', TRANSFER_IN, D('200.00'))])
        flow = build_cash_flow(self.accounts, {}, lines)
        self.assertEqual((flow.inflow, flow.outflow, flow.net, flow.transfers),
                         (D('500.00'), 0, D('500.00'), D('200.00')))

    def test_proportional_share_keeps_every_cent(self):  # INV-04
        entry = uuid4()
        lines = [EntryMoneyLine(entry, self.cash, D('100.00')), EntryMoneyLine(entry, self.bank, D('100.00')),
                 EntryMoneyLine(entry, self.third, D('-100.01'))]
        moves = build_cash_flow_movements(lines, self.names)
        received = sum((m.amount for m in moves if m.kind == TRANSFER_IN), D('0'))
        self.assertEqual(received, D('100.01'))
        self.assertEqual(sum((m.amount for m in moves if m.kind == INFLOW), D('0')), D('99.99'))

    def test_account_totals_add_up_to_the_consolidated_flow(self):  # INV-03
        e1, e2, e3 = uuid4(), uuid4(), uuid4()
        lines = [EntryMoneyLine(e1, self.cash, D('150.00')), EntryMoneyLine(e2, self.cash, D('-40.00')),
                 EntryMoneyLine(e2, self.bank, D('10.00')), EntryMoneyLine(e3, self.bank, D('-25.00')),
                 EntryMoneyLine(e3, self.third, D('25.00'))]
        flow = build_cash_flow(self.accounts, {self.cash: D('5.00')}, lines)
        self.assertEqual(sum((a.inflow for a in flow.accounts), D('0')), flow.inflow)
        self.assertEqual(sum((a.outflow for a in flow.accounts), D('0')), flow.outflow)
        self.assertEqual(sum((a.transfers_in for a in flow.accounts), D('0')), flow.transfers)
        self.assertEqual(sum((a.transfers_out for a in flow.accounts), D('0')), flow.transfers)
        for a in flow.accounts:
            self.assertEqual(a.net, a.inflow - a.outflow + a.transfers_in - a.transfers_out)
            self.assertEqual(a.closing, a.opening + a.net)


class CashFlowApiBase(AccountingApiBase):
    def setUp(self):
        super().setUp()
        enable(self.company_a, 'accounting')
        enable(self.company_b, 'accounting')
        cid = self.company_a.id
        self.cash = money_account(DjangoAccountRepository(cid), 'Caja', '1101', kind='CASH')
        self.bank = money_account(DjangoAccountRepository(cid), 'Banco', '1102')
        self.receivable = make_account(cid, 'Por cobrar', 'ASSET', '1201')
        self.income = make_account(cid, 'Ingresos', 'INCOME', '4101')
        self.expense = make_account(cid, 'Gastos', 'EXPENSE', '6101')
        make_period(cid)
        make_period(self.company_b.id)
        SettingsModel.objects.create(company_id=cid, cutoff_date=date(2026, 4, 1))

    def post(self, debit, credit, amount, on=DAY, description='Asiento', **extra):
        return services.post_journal_entry(self.company_a.id, services.JournalEntryInput(
            on, description, [services.JournalLineInput(debit.id, debit=D(amount)),
                              services.JournalLineInput(credit.id, credit=D(amount))], **extra))

    def summary(self, **params):
        params = {'date_from': '2026-05-01', 'date_to': '2026-05-31', **params}
        response = self.client_a.get(URL, params)
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def moves(self, **params):
        params = {'date_from': '2026-05-01', 'date_to': '2026-05-31', **params}
        response = self.client_a.get(MOVES, params)
        self.assertEqual(response.status_code, 200, response.data)
        return response.data


class CashFlowApiTests(CashFlowApiBase):
    def test_summary_matches_the_ledger_report_and_the_card_scenario(self):  # AC-01, AC-03
        self.post(self.cash, self.income, '2477.00')
        self.post(self.expense, self.cash, '1750.00')
        data = self.summary()
        report = services.get_ledger_report(self.company_a.id, FROM, TO)
        self.assertEqual((data['summary']['opening'], data['summary']['inflow'], data['summary']['outflow'],
                          data['summary']['net'], data['summary']['closing']),
                         ('0.00', '2477.00', '1750.00', '727.00', '727.00'))
        self.assertEqual((data['summary']['net'], data['summary']['closing']),
                         (f'{report.cash_flow.net:.2f}', f'{report.cash_flow.closing:.2f}'))
        self.assertFalse(data['coverage']['partial'])

    def test_account_balances_match_the_ledger_and_movements_back_the_totals(self):  # AC-02
        self.post(self.cash, self.income, '100.00', on=date(2026, 4, 20))
        self.post(self.cash, self.income, '300.00')
        self.post(self.expense, self.cash, '50.00')
        self.post(self.bank, self.cash, '40.00')
        data = self.summary()
        balances = services.journal_balances(self.company_a.id, [self.cash.id, self.bank.id])
        by_name = {a['name']: a for a in data['accounts']}
        for account, name in ((self.cash, 'Caja'), (self.bank, 'Banco')):
            ledger = balances[account.id].debit - balances[account.id].credit
            self.assertEqual(by_name[name]['closing'], f'{ledger:.2f}')
        self.assertEqual((by_name['Caja']['opening'], by_name['Caja']['closing']), ('100.00', '310.00'))
        result = self.moves()
        totals = result['totals']
        self.assertEqual((totals['inflow'], totals['outflow'], totals['transfers_in'], totals['transfers_out']),
                         (data['summary']['inflow'], data['summary']['outflow'], data['summary']['transfers'],
                          data['summary']['transfers']))
        self.assertEqual(result['count'], 5)

    def test_transfer_shows_sent_in_cash_and_received_in_bank(self):  # AC-04
        self.post(self.bank, self.cash, '500.00', description='Depósito')
        data = self.summary()
        by_name = {a['name']: a for a in data['accounts']}
        self.assertEqual((by_name['Caja']['transfers_out'], by_name['Banco']['transfers_in']), ('500.00', '500.00'))
        self.assertEqual((data['summary']['inflow'], data['summary']['outflow'], data['summary']['net']),
                         ('0.00', '0.00', '0.00'))
        kinds = {(m['account']['name'], m['kind']) for m in self.moves()['results']}
        self.assertEqual(kinds, {('Caja', 'transfer_out'), ('Banco', 'transfer_in')})

    def test_movement_has_the_entry_and_origin(self):  # AC-05
        entry = self.post(self.cash, self.income, '90.00', description='Cobro', origin_kind='SERVICE_PAYMENT',
                          origin_id=uuid4()).entry
        row = self.moves()['results'][0]
        self.assertEqual((row['entry_id'], row['description'], row['kind'], row['amount'], row['accounting_date']),
                         (str(entry.id), 'Cobro', 'inflow', '90.00', '2026-05-10'))
        self.assertEqual(row['origin']['kind'], 'SERVICE_PAYMENT')
        self.assertFalse(self.post(self.cash, self.income, '1.00').entry is None)
        self.assertIsNone([m for m in self.moves()['results'] if m['amount'] == '1.00'][0]['origin'])

    def test_filters_by_account_type_and_range(self):  # AC-06
        self.post(self.cash, self.income, '300.00')
        self.post(self.bank, self.income, '80.00')
        self.post(self.expense, self.cash, '50.00')
        self.post(self.bank, self.cash, '40.00')
        self.assertEqual(self.moves(account_id=str(self.bank.id))['count'], 2)
        self.assertEqual({m['kind'] for m in self.moves(type='transfer')['results']}, {'transfer_in', 'transfer_out'})
        self.assertEqual([m['amount'] for m in self.moves(type='outflow')['results']], ['50.00'])
        both = self.moves(type='inflow', account_id=str(self.cash.id))
        self.assertEqual([m['amount'] for m in both['results']], ['300.00'])
        self.assertEqual(self.moves(date_from='2026-05-11')['count'], 0)
        self.assertEqual(self.moves(page_size=2)['count'], 6)
        self.assertEqual(len(self.moves(page_size=2)['results']), 2)

    def test_invalid_parameters_and_foreign_or_non_money_accounts_are_rejected(self):  # AC-06
        self.assertEqual(self.client_a.get(URL).status_code, 400)
        self.assertEqual(self.client_a.get(URL, {'date_from': '2026-06-01', 'date_to': '2026-05-01'}).status_code, 400)
        self.assertEqual(self.client_a.get(MOVES, {'date_from': 'x', 'date_to': '2026-05-01'}).status_code, 400)
        self.assertEqual(self.client_a.get(MOVES, {'date_from': '2026-05-01', 'date_to': '2026-05-31',
                                                   'type': 'otro'}).status_code, 400)
        for account in (self.receivable, make_account(self.company_b.id, 'Caja B', 'ASSET', '1109')):
            response = self.client_a.get(MOVES, {'date_from': '2026-05-01', 'date_to': '2026-05-31',
                                                 'account_id': str(account.id)})
            self.assertEqual(response.status_code, 400)

    def test_reversal_is_an_outflow_on_its_own_date_marked_as_reversal(self):  # AC-07
        original = self.post(self.cash, self.income, '400.00', on=date(2026, 5, 20)).entry
        services.reverse_journal_entry(self.company_a.id, original.id, date(2026, 5, 25), 'Error')
        rows = self.moves()['results']
        self.assertEqual([(m['kind'], m['accounting_date'], m['is_reversal']) for m in rows],
                         [('outflow', '2026-05-25', True), ('inflow', '2026-05-20', False)])

    def test_cutoff_marks_partial_coverage_and_excludes_earlier_lines(self):
        make_period(self.company_a.id, 'Q1', date(2026, 1, 1), date(2026, 3, 31))
        self.post(self.cash, self.income, '700.00', on=date(2026, 3, 15))
        self.post(self.cash, self.income, '100.00')
        data = self.summary(date_from='2026-03-01')
        self.assertTrue(data['coverage']['partial'])
        self.assertEqual(data['summary']['inflow'], '100.00')
        self.assertEqual(self.moves(date_from='2026-03-01')['count'], 1)

    def test_no_data_leaks_between_companies_and_the_module_gate_applies(self):  # AC-08
        self.post(self.cash, self.income, '300.00')
        other = self.client_b.get(URL, {'date_from': '2026-05-01', 'date_to': '2026-05-31'})
        self.assertEqual((other.data['summary']['inflow'], other.data['accounts']), ('0.00', []))
        moves = self.client_b.get(MOVES, {'date_from': '2026-05-01', 'date_to': '2026-05-31'})
        self.assertEqual(moves.data['count'], 0)
        CompanyModuleModel.objects.filter(company_id=self.company_a.id, module_key='accounting').delete()
        response = self.client_a.get(URL, {'date_from': '2026-05-01', 'date_to': '2026-05-31'})
        self.assertEqual((response.status_code, response.data['code']), (403, 'module_disabled'))
