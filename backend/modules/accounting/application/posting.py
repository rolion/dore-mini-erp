"""Casos de uso de la configuración de asientos automáticos (CONT-12): describir, asignar y resolver cuentas."""
from dataclasses import dataclass, field
from uuid import UUID

from modules.accounting.domain.account import Account, AccountValidationError, MethodMapping
from modules.accounting.domain.catalog import METHOD_CODES, METHOD_LABELS
from modules.accounting.domain.classification import Classification, ClassificationNotFound
from modules.accounting.domain.posting import (
    CREDIT,
    DEBIT,
    SOURCE_CATEGORY,
    SOURCE_METHOD,
    SOURCE_ROLE,
    Event,
    PostingIssue,
    PostingNotFound,
    Role,
    account_problem,
    events_for,
    get_role,
    issue_invalid,
    issue_unconfigured,
    location,
    modules_using,
    roles_of,
    validate_account_for_role,
)


@dataclass(frozen=True)
class AccountInfo:
    id: UUID
    code: str | None
    name: str
    is_active: bool


@dataclass(frozen=True)
class RoleRow:
    role: str
    label: str
    account_class: str
    account: AccountInfo | None
    issue: str | None
    shared_with: tuple[str, ...] = ()  # otros módulos que usan el mismo rol


@dataclass(frozen=True)
class MethodRow:
    code: str
    label: str
    is_active: bool
    account: AccountInfo | None
    issue: str | None


@dataclass(frozen=True)
class CategoryRow:
    classification_id: UUID
    name: str
    is_active: bool
    account: AccountInfo | None
    issue: str | None


@dataclass(frozen=True)
class PreviewLine:
    side: str  # DEBIT | CREDIT
    role: str
    label: str
    account: AccountInfo | None
    status: str  # ok | missing | invalid | by_method | by_category


@dataclass(frozen=True)
class EventView:
    code: str
    label: str
    preview: tuple[PreviewLine, ...]
    issues: tuple[PostingIssue, ...]


@dataclass(frozen=True)
class ConfigView:
    module: str
    ready: bool
    events: tuple[EventView, ...]
    roles: tuple[RoleRow, ...] = ()
    methods: tuple[MethodRow, ...] = ()
    categories: tuple[CategoryRow, ...] = ()


@dataclass
class Context:
    """Foto de la configuración de una empresa para resolver eventos sin consultas repetidas."""
    accounts: dict[UUID, Account]
    disabled: frozenset[str]
    roles: dict[str, UUID]
    categories: dict[UUID, UUID]
    methods: dict[str, MethodMapping]
    classifications: dict[UUID, Classification]
    expense_categories: list[Classification] = field(default_factory=list)


def load_context(accounts, classes, posting, mappings, classifications) -> Context:
    by_id = classifications.list()
    return Context(
        accounts=accounts.by_id(), disabled=classes.disabled(), roles=posting.roles(),
        categories=posting.categories(), methods={m.code: m for m in mappings.all()},
        classifications={c.id: c for c in by_id},
        expense_categories=[c for c in by_id if c.direction == 'EXPENSE'])


def _info(account: Account | None) -> AccountInfo | None:
    return AccountInfo(account.id, account.code, account.name, account.is_active) if account else None


def _resolve_line(role: Role, event: Event, ctx: Context, method, classification_id):
    """`(account_id | None, issue | None)` de una línea del evento."""
    module = event.module
    if role.source == SOURCE_ROLE:
        account_id, subject = ctx.roles.get(role.code), role.label
        if account_id is None:
            return None, issue_unconfigured(role, module)
    elif role.source == SOURCE_METHOD:
        mapping = ctx.methods.get(str(method).upper()) if method else None
        if mapping is None:
            return None, PostingIssue('method_required', role.code, role.label, module,
                                      'Indique un método de pago válido para la operación.')
        subject = f'{role.label} · {METHOD_LABELS[mapping.code]}'
        if not mapping.is_active or mapping.account_id is None:
            return None, PostingIssue(
                'method_unconfigured', role.code, subject, module,
                f'Falta la cuenta Caja o Banco del método «{METHOD_LABELS[mapping.code]}». '
                f'Configúrela en {location(module)}.')
        account_id = mapping.account_id
    else:
        category = ctx.classifications.get(classification_id) if classification_id else None
        if category is None or category.direction != 'EXPENSE':
            return None, PostingIssue('category_required', role.code, role.label, module,
                                      'Indique una categoría de gasto válida para la operación.')
        subject = f'{role.label} · {category.name}'
        account_id = ctx.categories.get(category.id)
        if account_id is None:
            return None, PostingIssue(
                'category_unconfigured', role.code, subject, module,
                f'Falta la cuenta de gasto de la categoría «{category.name}». Configúrela en {location(module)}.')
    problem = account_problem(role, ctx.accounts.get(account_id), ctx.disabled)
    if problem:
        return None, issue_invalid(role, subject, module, problem)
    return account_id, None


def resolve_event(event: Event, ctx: Context, method=None, classification_id=None):
    """Cuentas por rol de un evento concreto (método/categoría de la operación) y los faltantes que impiden usarlo."""
    accounts: dict[str, UUID] = {}
    issues: list[PostingIssue] = []
    for _, role in event.lines:
        account_id, issue = _resolve_line(role, event, ctx, method, classification_id)
        if issue:
            issues.append(issue)
        else:
            accounts[role.code] = account_id
    return accounts, issues


def event_issues(event: Event, ctx: Context) -> list[PostingIssue]:
    """Faltantes del evento para cualquier operación futura: roles fijos, y todos los métodos y categorías activos."""
    found: list[PostingIssue] = []
    for _, role in event.lines:
        if role.source == SOURCE_ROLE:
            _, issue = _resolve_line(role, event, ctx, None, None)
            found += [issue] if issue else []
        elif role.source == SOURCE_METHOD:
            for mapping in ctx.methods.values():
                if mapping.is_active:
                    _, issue = _resolve_line(role, event, ctx, mapping.code, None)
                    found += [issue] if issue else []
        else:
            for category in ctx.expense_categories:
                if category.is_active:
                    _, issue = _resolve_line(role, event, ctx, None, category.id)
                    found += [issue] if issue else []
    return found


def _preview(event: Event, ctx: Context) -> tuple[PreviewLine, ...]:
    lines = []
    for side, role in event.lines:
        if role.source == SOURCE_METHOD:
            lines.append(PreviewLine(side, role.code, role.label, None, 'by_method'))
        elif role.source == SOURCE_CATEGORY:
            lines.append(PreviewLine(side, role.code, role.label, None, 'by_category'))
        else:
            account_id = ctx.roles.get(role.code)
            account = ctx.accounts.get(account_id) if account_id else None
            status = ('missing' if account_id is None else
                      'invalid' if account_problem(role, account, ctx.disabled) else 'ok')
            lines.append(PreviewLine(side, role.code, role.label, _info(account), status))
    return tuple(lines)


class DescribePostingConfig:
    def __init__(self, accounts, classes, posting, mappings, classifications):
        self.sources = (accounts, classes, posting, mappings, classifications)

    def execute(self, module: str) -> ConfigView:
        events = events_for(module)
        ctx = load_context(*self.sources)
        views = tuple(EventView(e.code, e.label, _preview(e, ctx), tuple(event_issues(e, ctx))) for e in events)
        roles = []
        for role in roles_of(module, SOURCE_ROLE):
            account_id = ctx.roles.get(role.code)
            account = ctx.accounts.get(account_id) if account_id else None
            problem = account_problem(role, account, ctx.disabled) if account_id else None
            roles.append(RoleRow(role.code, role.label, role.account_class, _info(account), problem,
                                 tuple(m for m in modules_using(role.code) if m != module)))
        methods = ()
        if roles_of(module, SOURCE_METHOD):
            money = roles_of(module, SOURCE_METHOD)[0]
            rows = []
            for code in METHOD_CODES:
                mapping = ctx.methods[code]
                account = ctx.accounts.get(mapping.account_id) if mapping.account_id else None
                issue = None
                if mapping.is_active:
                    issue = (account_problem(money, account, ctx.disabled) if account else
                             'Falta la cuenta Caja o Banco de este método.')
                rows.append(MethodRow(code, METHOD_LABELS[code], mapping.is_active, _info(account), issue))
            methods = tuple(rows)
        categories = ()
        if roles_of(module, SOURCE_CATEGORY):
            role = roles_of(module, SOURCE_CATEGORY)[0]
            rows = []
            for category in ctx.expense_categories:
                account_id = ctx.categories.get(category.id)
                account = ctx.accounts.get(account_id) if account_id else None
                issue = (account_problem(role, account, ctx.disabled) if account_id else
                         ('Falta la cuenta de gasto de esta categoría.' if category.is_active else None))
                rows.append(CategoryRow(category.id, category.name, category.is_active, _info(account), issue))
            categories = tuple(rows)
        return ConfigView(module, not any(v.issues for v in views), views, tuple(roles), methods, categories)


class SetRoleAccount:
    """Asigna (o quita con `None`) la cuenta de un rol fijo. Un uso nuevo se valida; no se tocan asientos."""

    def __init__(self, accounts, classes, posting):
        self.accounts, self.classes, self.posting = accounts, classes, posting

    def execute(self, role_code: str, account_id: UUID | None) -> None:
        role = get_role(role_code)
        if role.source != SOURCE_ROLE:
            raise PostingNotFound(role_code)
        if account_id is not None:
            validate_account_for_role(role, self.accounts.get(account_id), self.classes.disabled())
        self.posting.set('ROLE', role.code, account_id)


class SetCategoryAccount:
    def __init__(self, accounts, classes, classifications, posting):
        self.accounts, self.classes = accounts, classes
        self.classifications, self.posting = classifications, posting

    def execute(self, classification_id: UUID, account_id: UUID | None) -> None:
        category = self.classifications.get(classification_id)
        if category is None:
            raise ClassificationNotFound(str(classification_id))
        if category.direction != 'EXPENSE':
            raise AccountValidationError({'classification_id': ['La categoría no es de gasto.']})
        if account_id is not None:
            validate_account_for_role(get_role('EXPENSE_BY_CATEGORY'), self.accounts.get(account_id),
                                      self.classes.disabled())
        self.posting.set('CATEGORY', str(category.id), account_id)


__all__ = ['AccountInfo', 'CategoryRow', 'ConfigView', 'Context', 'CREDIT', 'DEBIT', 'DescribePostingConfig',
           'EventView', 'MethodRow', 'PreviewLine', 'RoleRow', 'SetCategoryAccount', 'SetRoleAccount',
           'event_issues', 'load_context', 'resolve_event']
