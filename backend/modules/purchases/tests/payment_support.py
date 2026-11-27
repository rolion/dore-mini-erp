"""Contabilidad de prueba para pagos de Compras: cuentas por rol, métodos de pago con cuenta y un período abierto."""
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from modules.accounting import services as accounting
from modules.accounting.application.use_cases import ConfigureMethod
from modules.accounting.infrastructure.django.models import JournalEntryModel
from modules.accounting.infrastructure.django.repositories import DjangoAccountRepository, DjangoMethodMappingRepository
from modules.accounting.infrastructure.django.models import FiscalPeriodModel
from modules.accounting.tests.journal_support import make_account, make_period, money_account
from modules.modularity.domain.modules import DEFAULT_ENABLED_KEYS
from modules.modularity.tests.test_enforcement import set_enabled

TODAY = timezone.localdate()


class PaymentBooks:
    """Cuentas y configuración contable de una empresa de prueba con Compras y Contabilidad habilitadas."""

    def __init__(self, company, *, advances=True, payable=True, extra_modules=()):
        set_enabled(company, (*DEFAULT_ENABLED_KEYS, 'purchases', 'accounting', *extra_modules))
        self.company = company
        accounts = DjangoAccountRepository(company.id)
        self.caja = money_account(accounts, 'Caja', '110101', 'CASH')
        self.banco = money_account(accounts, 'Banco', '110102')
        self.inventory = make_account(company.id, 'Inventario', 'ASSET', '113001')
        self.payable = make_account(company.id, 'Proveedores', 'LIABILITY', '210101')
        self.advances = make_account(company.id, 'Anticipos a proveedores', 'ASSET', '113101')
        FiscalPeriodModel.objects.filter(company_id=company.id).delete()  # reemplaza el período amplio de pruebas
        self.period = make_period(company.id, 'Año', TODAY - timedelta(days=200), TODAY + timedelta(days=100))
        for method, account in (('CASH', self.caja), ('BANK_TRANSFER', self.banco), ('QR', self.banco)):
            self.map_method(method, account)
        accounting.set_role_account(company.id, 'INVENTORY', self.inventory.id)
        if payable:
            accounting.set_role_account(company.id, 'PAYABLE', self.payable.id)
        if advances:
            accounting.set_role_account(company.id, 'SUPPLIER_ADVANCES', self.advances.id)

    def map_method(self, method, account, active=True):
        with transaction.atomic():
            ConfigureMethod(DjangoAccountRepository(self.company.id), DjangoMethodMappingRepository(self.company.id)
                            ).execute(method, account.id, active)

    def journal(self, kind=None):
        rows = JournalEntryModel.objects.filter(company_id=self.company.id)
        return rows.filter(origin_kind=kind) if kind else rows

    def net(self, account):
        """(debe, haber) acumulados de la cuenta en el libro de asientos."""
        balance = accounting.journal_balances(self.company.id, [account.id]).get(account.id)
        return (balance.debit, balance.credit) if balance else (0, 0)

    def lines(self, kind, origin_id):
        entry = self.journal(kind).get(origin_id=origin_id)
        return sorted((line.account_id, line.debit, line.credit) for line in entry.lines.all())
