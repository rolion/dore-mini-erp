import { AccountClassCode, ProblemInfo } from './accounting';

/** Módulos que tienen eventos contabilizables (los mismos del catálogo del servidor). */
export type PostingModule = 'sales' | 'receivables' | 'inventory' | 'purchases' | 'expenses';

export type PostingSide = 'DEBIT' | 'CREDIT';
/** `by_method` / `by_category`: la cuenta depende de la operación (método de pago o categoría de gasto). */
export type PreviewStatus = 'ok' | 'missing' | 'invalid' | 'by_method' | 'by_category';

export interface PostingAccount {
  id: string;
  code: string | null;
  name: string;
  isActive: boolean;
}

export interface PreviewLine {
  side: PostingSide;
  role: string;
  label: string;
  account: PostingAccount | null;
  status: PreviewStatus;
}

export interface PostingIssue {
  code: string;
  role: string;
  subject: string;
  module: string;
  /** Mensaje en español de respaldo; el panel arma el texto en el idioma activo con `code`, `params` y `problem`. */
  message: string;
  params: Record<string, string>;
  problem: ProblemInfo | null;
}

export interface PostingEvent {
  code: string;
  label: string;
  preview: PreviewLine[];
  issues: PostingIssue[];
}

export interface SharedModule {
  module: string;
  label: string;
}

export interface RoleRow {
  role: string;
  label: string;
  accountClass: AccountClassCode;
  account: PostingAccount | null;
  issue: string | null;
  problem: ProblemInfo | null;
  sharedWith: SharedModule[];
}

export interface MethodRow {
  code: string;
  label: string;
  isActive: boolean;
  account: PostingAccount | null;
  issue: string | null;
  problem: ProblemInfo | null;
}

/** Cuenta de gasto configurada para una categoría de Gastos (Contabilidad solo conoce su id). */
export interface CategoryRow {
  categoryId: string;
  account: PostingAccount | null;
  issue: string | null;
  problem: ProblemInfo | null;
}

/** Categoría de Gastos que el módulo anfitrión entrega al panel (nombre y estado son de Gastos). */
export interface PostingCategory {
  id: string;
  name: string;
  isActive: boolean;
}

export interface PostingConfig {
  module: PostingModule;
  moduleLabel: string;
  accountingEnabled: boolean;
  ready: boolean;
  events: PostingEvent[];
  roles: RoleRow[];
  methods: MethodRow[];
  categories: CategoryRow[];
}

// --- Formas del servidor (snake_case) ---

export interface PostingAccountDto {
  id: string;
  code: string | null;
  name: string;
  is_active: boolean;
}

export interface RoleRowDto {
  role: string;
  label: string;
  account_class: AccountClassCode;
  account: PostingAccountDto | null;
  issue: string | null;
  problem: ProblemInfo | null;
  shared_with: SharedModule[];
}

export interface MethodRowDto {
  code: string;
  label: string;
  is_active: boolean;
  account: PostingAccountDto | null;
  issue: string | null;
  problem: ProblemInfo | null;
}

export interface CategoryRowDto {
  category_id: string;
  account: PostingAccountDto | null;
  issue: string | null;
  problem: ProblemInfo | null;
}

export interface PostingConfigDto {
  module: PostingModule;
  module_label: string;
  accounting_enabled: boolean;
  ready: boolean;
  events: {
    code: string;
    label: string;
    preview: { side: PostingSide; role: string; label: string; account: PostingAccountDto | null; status: PreviewStatus }[];
    issues: PostingIssue[];
  }[];
  roles: RoleRowDto[];
  methods: MethodRowDto[];
  categories: CategoryRowDto[];
}

const account = (dto: PostingAccountDto | null): PostingAccount | null =>
  dto ? { id: dto.id, code: dto.code, name: dto.name, isActive: dto.is_active } : null;

export const toRoleRow = (dto: RoleRowDto): RoleRow => ({
  role: dto.role,
  label: dto.label,
  accountClass: dto.account_class,
  account: account(dto.account),
  issue: dto.issue,
  problem: dto.problem,
  sharedWith: dto.shared_with,
});

export const toCategoryRow = (dto: CategoryRowDto): CategoryRow => ({
  categoryId: dto.category_id,
  account: account(dto.account),
  issue: dto.issue,
  problem: dto.problem,
});

export function toPostingConfig(dto: PostingConfigDto): PostingConfig {
  return {
    module: dto.module,
    moduleLabel: dto.module_label,
    accountingEnabled: dto.accounting_enabled,
    ready: dto.ready,
    events: dto.events.map((event) => ({
      code: event.code,
      label: event.label,
      issues: event.issues,
      preview: event.preview.map((line) => ({ ...line, account: account(line.account) })),
    })),
    roles: dto.roles.map(toRoleRow),
    methods: dto.methods.map((m) => ({
      code: m.code,
      label: m.label,
      isActive: m.is_active,
      account: account(m.account),
      issue: m.issue,
      problem: m.problem,
    })),
    categories: dto.categories.map(toCategoryRow),
  };
}

/** Nombre mostrable de una cuenta: «código · nombre» (o solo el nombre si no tiene código). */
export const accountLabel = (a: { code?: string | null; name: string }): string => (a.code ? `${a.code} · ${a.name}` : a.name);
