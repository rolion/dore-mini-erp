"""CONT-05: reporte contable del libro (flujo de dinero, resultado, cobertura). AC-01..AC-05; INV-R1..R5."""
from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.test import SimpleTestCase, TestCase

from modules.accounting import services
from modules.accounting.domain.coverage import Gap
from modules.accounting.domain.ledger_report import (
    EntryMoneyLine,
    MoneyAccount,
    build_cash_flow,
    build_coverage,
    build_result,
)
from modules.accounting.infrastructure.django.models import SettingsModel
from modules.accounting.infrastructure.django.repositories import DjangoAccountRepository
from modules.accounting.tests.journal_support import make_account, make_period, money_account
from modules.accounts.testing import make_company

D = Decimal
DAY = date(2026, 5, 10)
FROM, TO = date(2026, 5, 1), date(2026, 5, 31)


class LedgerDomainTests(SimpleTestCase):
    def test_transfer_between_money_accounts_is_neither_inflow_nor_outflow(self):  # AC-03, INV-R1
        cash, bank, entry = uuid4(), uuid4(), uuid4()
        flow = build_cash_flow([MoneyAccount(cash, 'Caja'), MoneyAccount(bank, 'Banco')], {cash: D('500.00')},
                               [EntryMoneyLine(entry, cash, D('-200.00')), EntryMoneyLine(entry, bank, D('200.00'))])
        self.assertEqual((flow.inflow, flow.outflow, flow.net, flow.transfers), (0, 0, 0, D('200.00')))
        self.assertEqual((flow.opening, flow.closing), (D('500.00'), D('500.00')))

    def test_entries_split_into_inflow_and_outflow_by_their_money_net(self):  # INV-R1
        cash = uuid4()
        flow = build_cash_flow([MoneyAccount(cash, 'Caja')], {},
                               [EntryMoneyLine(uuid4(), cash, D('150.00')),
                                EntryMoneyLine(uuid4(), cash, D('-300.00'))])
        self.assertEqual((flow.inflow, flow.outflow, flow.net, flow.closing), (D('150.00'), D('300.00'), D('-150.00'),
                                                                               D('-150.00')))

    def test_result_is_income_minus_cost_minus_expense(self):  # INV-R2
        result = build_result({'INCOME': (D('0'), D('150')), 'COST': (D('100'), D('0')), 'EXPENSE': (D('20'), D('5'))})
        self.assertEqual((result.income, result.cost, result.margin, result.expense, result.result),
                         (D('150'), D('100'), D('50'), D('15'), D('35')))

    def test_coverage_is_partial_before_the_cutoff_or_across_a_gap(self):  # AC-05
        cutoff = date(2026, 5, 1)
        self.assertTrue(build_coverage(cutoff, [], date(2026, 4, 20), date(2026, 5, 10)).partial)
        self.assertFalse(build_coverage(cutoff, [], date(2026, 5, 1), date(2026, 5, 31)).partial)
        self.assertTrue(build_coverage(cutoff, [Gap(date(2026, 5, 10), date(2026, 5, 20))], FROM, TO).partial)
        self.assertTrue(build_coverage(None, [], FROM, TO).partial)


class LedgerReportBase(TestCase):
    def setUp(self):
        self.company = make_company('A')
        self.other = make_company('B')
        cid = self.company.id
        self.cash = money_account(DjangoAccountRepository(cid), 'Caja', '1101', kind='CASH')
        self.bank = money_account(DjangoAccountRepository(cid), 'Banco', '1102')
        self.receivable = make_account(cid, 'Por cobrar', 'ASSET', '1201')
        self.inventory = make_account(cid, 'Inventario', 'ASSET', '1301')
        self.payable = make_account(cid, 'Por pagar', 'LIABILITY', '2101')
        self.income = make_account(cid, 'Ingresos', 'INCOME', '4101')
        self.cost = make_account(cid, 'Costo de ventas', 'COST', '5101')
        self.expense = make_account(cid, 'Gastos', 'EXPENSE', '6101')
        make_period(cid)
        SettingsModel.objects.create(company_id=cid, cutoff_date=date(2026, 4, 1))

    def post(self, debit, credit, amount, on=DAY, company=None):
        company = company or self.company
        return services.post_journal_entry(company.id, services.JournalEntryInput(
            on, 'Asiento', [services.JournalLineInput(debit.id, debit=D(amount)),
                            services.JournalLineInput(credit.id, credit=D(amount))]))

    def report(self, date_from=FROM, date_to=TO):
        return services.get_ledger_report(self.company.id, date_from, date_to)


class LedgerReportTests(LedgerReportBase):
    def test_sale_cost_and_collection_do_not_duplicate_income(self):  # AC-01
        self.post(self.receivable, self.income, '150.00')
        self.post(self.cost, self.inventory, '100.00')
        self.post(self.cash, self.receivable, '150.00')
        report = self.report()
        self.assertEqual((report.result.income, report.result.cost, report.result.margin),
                         (D('150.00'), D('100.00'), D('50.00')))
        self.assertEqual((report.cash_flow.inflow, report.cash_flow.outflow), (D('150.00'), 0))

    def test_buying_inventory_and_paying_part_is_an_outflow_not_an_expense(self):  # AC-02
        self.post(self.inventory, self.payable, '1000.00')
        self.post(self.payable, self.cash, '300.00')
        report = self.report()
        self.assertEqual((report.cash_flow.outflow, report.cash_flow.inflow, report.cash_flow.net),
                         (D('300.00'), 0, D('-300.00')))
        self.assertEqual((report.result.expense, report.result.cost, report.result.result), (0, 0, 0))

    def test_a_transfer_keeps_the_net_flow_at_zero(self):  # AC-03
        self.post(self.cash, self.income, '500.00')
        self.post(self.bank, self.cash, '200.00')
        flow = self.report().cash_flow
        self.assertEqual((flow.inflow, flow.outflow, flow.net, flow.transfers),
                         (D('500.00'), 0, D('500.00'), D('200.00')))
        by_name = {a.name: a.net for a in flow.accounts}
        self.assertEqual(by_name, {'Caja': D('300.00'), 'Banco': D('200.00')})

    def test_company_dates_and_reversals_by_accounting_date(self):  # AC-04, INV-R4, INV-R5
        original = self.post(self.cash, self.income, '400.00', on=date(2026, 5, 20))
        services.reverse_journal_entry(self.company.id, original.entry.id, date(2026, 6, 5), 'Error')
        may, june = self.report(FROM, TO), self.report(date(2026, 6, 1), date(2026, 6, 30))
        self.assertEqual(may.cash_flow.net, D('400.00'))
        self.assertEqual((june.cash_flow.outflow, june.cash_flow.opening, june.cash_flow.closing),
                         (D('400.00'), D('400.00'), 0))
        self.assertEqual((june.result.income, may.result.income), (D('-400.00'), D('400.00')))
        self.assertEqual(self.report(date(2026, 5, 21), date(2026, 5, 31)).cash_flow.net, 0)
        empty = services.get_ledger_report(self.other.id, FROM, TO)
        self.assertEqual((empty.cash_flow.net, empty.result.result, len(empty.cash_flow.accounts)), (0, 0, 0))

    def test_entries_before_the_cutoff_are_not_summed(self):  # AC-05, INV-R5
        make_period(self.company.id, 'Q1', date(2026, 1, 1), date(2026, 3, 31))
        self.post(self.cash, self.income, '700.00', on=date(2026, 3, 15))  # anterior al corte (2026-04-01)
        self.post(self.cash, self.income, '100.00', on=DAY)
        report = self.report(date(2026, 3, 1), TO)
        self.assertEqual((report.partial, report.cash_flow.inflow, report.cash_flow.opening, report.result.income),
                         (True, D('100.00'), 0, D('100.00')))
        self.assertEqual(self.report(FROM, TO).cash_flow.opening, 0)

    def test_coverage_is_reported_by_cutoff(self):  # AC-05
        self.assertFalse(self.report().partial)
        early = self.report(date(2026, 3, 1), TO)
        self.assertTrue(early.partial)
        self.assertEqual(early.cutoff_date, date(2026, 4, 1))
