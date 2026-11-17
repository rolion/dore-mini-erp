"""Ayudas de pruebas del motor de asientos (CONT-02): cuentas clasificadas, períodos y entradas de ejemplo."""
from datetime import date
from decimal import Decimal
from uuid import uuid4

from modules.accounting import services
from modules.accounting.application.fiscal_periods import CreateFiscalPeriod
from modules.accounting.domain.account import Account
from modules.accounting.infrastructure.django.repositories import DjangoAccountRepository, DjangoFiscalPeriodRepository

DAY = date(2026, 5, 10)


def make_account(company_id, name, account_class='ASSET', code=None, currency='BOB', active=True):
    account = Account.create(name, currency, code=code or str(abs(hash((str(company_id), name))))[:8])
    account.classify(account_class)
    if not active:
        account.deactivate()
    return DjangoAccountRepository(company_id).save(account)


def make_period(company_id, name='Q2', start=date(2026, 4, 1), end=date(2026, 6, 30)):
    return CreateFiscalPeriod(DjangoFiscalPeriodRepository(company_id)).execute(name, start, end)


def sale_lines(cash, bank, income, cash_amount='200.00', bank_amount='300.00', income_amount='500.00'):
    return [services.JournalLineInput(cash.id, debit=Decimal(cash_amount)),
            services.JournalLineInput(bank.id, debit=Decimal(bank_amount)),
            services.JournalLineInput(income.id, credit=Decimal(income_amount))]


def entry_input(cash, bank, income, **overrides):
    data = dict(accounting_date=DAY, description='Servicio', lines=sale_lines(cash, bank, income), created_by=7,
                created_by_name='Ana')
    data.update(overrides)
    return services.JournalEntryInput(**data)


def automatic(**overrides):
    return dict(origin_kind='SERVICE_PAYMENT', origin_id=uuid4(), **overrides)


def money_account(accounts, name, code, kind='BANK'):
    """Cuenta de dinero válida para un método de pago (Activo, con código y tipo Caja/Banco), vía el repositorio."""
    from modules.accounting.domain.account import Account
    account = Account.create(name, 'BOB', kind=kind, code=code)
    account.classify('ASSET')
    return accounts.save(account)
