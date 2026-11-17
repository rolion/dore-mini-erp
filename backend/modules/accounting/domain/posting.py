"""Catálogo fijo de eventos contabilizables y roles de cuenta (CONT-12). Puro: sin Django.

No hay reglas definidas por la persona: cada módulo tiene eventos de dos líneas con un único importe y cada línea
nombra un *rol*. La empresa solo elige qué cuenta cumple cada rol (o cada categoría de gasto, o cada método de pago).
El código del evento es el `origin_kind` del asiento (≤ 30 caracteres).
"""
from dataclasses import dataclass, field

from .account import Account, AccountValidationError
from .catalog import FLOW_CURRENCY
from .account_class import ASSET, COST, EXPENSE, INCOME, LIABILITY
from .journal import ORIGIN_KIND_MAX

SOURCE_ROLE = 'ROLE'  # una cuenta por rol y empresa
SOURCE_METHOD = 'METHOD'  # cuenta de dinero según el método de pago (mapeo existente)
SOURCE_CATEGORY = 'CATEGORY'  # cuenta de gasto según la categoría del gasto

DEBIT = 'DEBIT'
CREDIT = 'CREDIT'

CLASS_LABELS: dict[str, str] = {ASSET: 'Activo', LIABILITY: 'Pasivo', INCOME: 'Ingresos', EXPENSE: 'Gastos',
                                COST: 'Costos'}

MODULE_LABELS: dict[str, str] = {'sales': 'Ventas', 'receivables': 'Cobros', 'inventory': 'Inventario',
                                 'purchases': 'Compras', 'expenses': 'Gastos'}


class PostingNotFound(Exception):
    """Rol, evento o módulo que no existe en el catálogo."""


@dataclass(frozen=True)
class Role:
    code: str
    label: str
    account_class: str
    source: str = SOURCE_ROLE


ROLES: dict[str, Role] = {r.code: r for r in (
    Role('SALES_INCOME', 'Ingresos por ventas', INCOME),
    Role('SERVICE_INCOME', 'Ingresos por servicios', INCOME),
    Role('RECEIVABLE', 'Cuentas por cobrar', ASSET),
    Role('CUSTOMER_ADVANCES', 'Anticipos de clientes', LIABILITY),
    Role('INVENTORY', 'Inventario', ASSET),
    Role('COST_OF_SALES', 'Costo de ventas', COST),
    Role('PAYABLE', 'Cuentas por pagar (proveedores)', LIABILITY),
    Role('MONEY', 'Cuenta de Activo del método de pago', ASSET, SOURCE_METHOD),
    Role('EXPENSE_BY_CATEGORY', 'Cuenta de gasto de la categoría', EXPENSE, SOURCE_CATEGORY),
)}


@dataclass(frozen=True)
class Event:
    code: str  # = origin_kind del asiento
    module: str
    label: str
    debit_role: str
    credit_role: str
    # Segunda línea de Debe opcional (p. ej. los anticipos aplicados al reconocer la entrega de un pedido).
    extra_debit_role: str | None = None
    # `False`: evento histórico; sigue reconocido (cobrar, revertir) pero ya no se configura ni se muestra.
    active: bool = True

    def __post_init__(self):
        roles = (self.debit_role, self.credit_role, *([self.extra_debit_role] if self.extra_debit_role else []))
        if len(self.code) > ORIGIN_KIND_MAX or any(role not in ROLES for role in roles):
            raise ValueError(f'Evento mal definido: {self.code}')

    @property
    def lines(self) -> tuple[tuple[str, Role], ...]:
        debits = [(DEBIT, ROLES[self.debit_role])]
        if self.extra_debit_role:
            debits.append((DEBIT, ROLES[self.extra_debit_role]))
        return (*debits, (CREDIT, ROLES[self.credit_role]))

    @property
    def role_codes(self) -> tuple[str, ...]:
        return tuple(role.code for _, role in self.lines)


EVENTS: tuple[Event, ...] = (
    # Ventas (VEN-01): el ingreso se reconoce al entregar; lo cobrado antes es un anticipo de cliente.
    Event('SALE_ADVANCE', 'sales', 'Cobrar un pedido por adelantado', 'MONEY', 'CUSTOMER_ADVANCES'),
    Event('SALE_DELIVERY', 'sales', 'Reconocer la entrega de un pedido', 'RECEIVABLE', 'SALES_INCOME',
          extra_debit_role='CUSTOMER_ADVANCES'),
    Event('SALE_PAYMENT', 'sales', 'Cobrar una venta', 'MONEY', 'RECEIVABLE'),
    Event('SALE_RECOGNITION', 'sales', 'Reconocer una venta (al confirmar, histórico)', 'RECEIVABLE', 'SALES_INCOME',
          active=False),
    # Cobros (SRV-01): el ingreso se reconoce al marcar el tratamiento como prestado; lo cobrado antes es anticipo.
    Event('SERVICE_ADVANCE', 'receivables', 'Cobrar un servicio por adelantado', 'MONEY', 'CUSTOMER_ADVANCES'),
    Event('SERVICE_RECOGNITION', 'receivables', 'Reconocer un servicio prestado', 'RECEIVABLE', 'SERVICE_INCOME',
          extra_debit_role='CUSTOMER_ADVANCES'),
    Event('SERVICE_PAYMENT', 'receivables', 'Cobrar un servicio', 'MONEY', 'RECEIVABLE'),
    Event('INVENTORY_SALE_COST', 'inventory', 'Costo de ventas por salida de inventario', 'COST_OF_SALES',
          'INVENTORY'),
    Event('PURCHASE_RECOGNITION', 'purchases', 'Reconocer una compra de mercadería', 'INVENTORY', 'PAYABLE'),
    Event('PURCHASE_PAYMENT', 'purchases', 'Pagar a un proveedor', 'PAYABLE', 'MONEY'),
    Event('EXPENSE_RECORD', 'expenses', 'Registrar un gasto', 'EXPENSE_BY_CATEGORY', 'MONEY'),
)
_BY_CODE = {e.code: e for e in EVENTS}


def get_event(code: object) -> Event:
    if isinstance(code, str) and code in _BY_CODE:
        return _BY_CODE[code]
    raise PostingNotFound(str(code))


def events_for(module: object) -> tuple[Event, ...]:
    found = tuple(e for e in EVENTS if e.module == module and e.active)
    if not found:
        raise PostingNotFound(str(module))
    return found


def get_role(code: object) -> Role:
    if isinstance(code, str) and code in ROLES:
        return ROLES[code]
    raise PostingNotFound(str(code))


def roles_of(module: str, source: str) -> list[Role]:
    """Roles distintos (en orden de aparición) con ese origen que usan los eventos del módulo."""
    seen: list[Role] = []
    for event in events_for(module):
        for _, role in event.lines:
            if role.source == source and role not in seen:
                seen.append(role)
    return seen


def modules_using(role_code: str) -> list[str]:
    """Módulos cuyos eventos usan el rol (para avisar que se comparte)."""
    return [m for m in MODULE_LABELS if any(role_code in e.role_codes for e in EVENTS
                                            if e.module == m and e.active)]


@dataclass(frozen=True)
class Problem:
    """Por qué una cuenta no sirve: `code` y `params` estables (el cliente traduce) y `message` en español."""
    code: str  # account_missing | account_inactive | currency | no_code_class | wrong_class | class_disabled
    params: dict = field(default_factory=dict)
    message: str = ''


def account_problem_info(role: Role, account: Account | None, disabled_classes: frozenset[str]) -> Problem | None:
    """Por qué la cuenta no sirve para el rol (código, parámetros y mensaje accionable) o `None` si sirve."""
    if account is None:
        return Problem('account_missing', {}, 'La cuenta no existe en esta empresa.')
    name = f'«{account.name}»'
    if not account.is_active:
        return Problem('account_inactive', {'account': account.name},
                       f'La cuenta {name} está deshabilitada; elija otra o actívela en Cuentas.')
    if account.currency != FLOW_CURRENCY:
        return Problem('currency', {'account': account.name, 'currency': FLOW_CURRENCY},
                       f'La cuenta {name} debe estar en {FLOW_CURRENCY}.')
    if account.account_class is None or account.code is None:
        return Problem('no_code_class', {'account': account.name},
                       f'La cuenta {name} no tiene código y clasificación contable; complétela en Cuentas.')
    if account.account_class != role.account_class:
        return Problem('wrong_class', {'account': account.name, 'actual': account.account_class,
                                       'required': role.account_class},
                       f'La cuenta {name} es de {CLASS_LABELS.get(account.account_class, account.account_class)}; '
                       f'se requiere una cuenta de {CLASS_LABELS[role.account_class]}.')
    if account.account_class in disabled_classes:
        return Problem('class_disabled', {'class_code': account.account_class},
                       f'La clasificación {CLASS_LABELS[account.account_class]} está deshabilitada.')
    return None


def account_problem(role: Role, account: Account | None, disabled_classes: frozenset[str]) -> str | None:
    """Mensaje en español de `account_problem_info`, o `None` si la cuenta sirve."""
    problem = account_problem_info(role, account, disabled_classes)
    return problem.message if problem else None


class AccountProblemError(AccountValidationError):
    """Cuenta no válida para un rol: además del mensaje por campo lleva el `Problem` estructurado."""

    def __init__(self, problem: Problem):
        super().__init__({'account_id': [problem.message]})
        self.problem = problem


def validate_account_for_role(role: Role, account: Account | None, disabled_classes: frozenset[str]) -> None:
    problem = account_problem_info(role, account, disabled_classes)
    if problem:
        raise AccountProblemError(problem)


@dataclass(frozen=True)
class PostingIssue:
    """Un faltante de configuración: `code` estable, el rol, lo que falta y qué hacer.

    `params` (y `problem` en `account_invalid`) permiten al cliente traducir el aviso; `message` va en español.
    """
    code: str  # role_unconfigured | account_invalid | method_unconfigured | method_required | category_unconfigured |
    #            category_required
    role: str
    subject: str  # rol, método o categoría afectado, legible
    module: str
    message: str
    params: dict = field(default_factory=dict)
    problem: Problem | None = None


def location(module: str) -> str:
    return f'{MODULE_LABELS[module]} › Configuración › Asientos automáticos'


def issue_unconfigured(role: Role, module: str) -> PostingIssue:
    return PostingIssue('role_unconfigured', role.code, role.label, module,
                        f'Falta configurar la cuenta «{role.label}». Configúrela en {location(module)}.')


def issue_invalid(role: Role, subject: str, module: str, problem: Problem) -> PostingIssue:
    return PostingIssue('account_invalid', role.code, subject, module,
                        f'{problem.message} Corrija «{subject}» en {location(module)}.', problem=problem)


class PostingConfigurationMissing(Exception):
    """Con Contabilidad habilitada y cobertura, falta o no sirve alguna cuenta: la operación no puede contabilizarse."""

    def __init__(self, issues: list[PostingIssue]):
        super().__init__('; '.join(i.message for i in issues))
        self.issues = issues
