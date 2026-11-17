import { AccountClassCode } from './accounting';

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
  message: string;
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
  sharedWith: SharedModule[];
}

export interface MethodRow {
  code: string;
  label: string;
  isActive: boolean;
  account: PostingAccount | null;
  issue: string | null;
}

export interface CategoryRow {
  classificationId: string;
  name: string;
  isActive: boolean;
  account: PostingAccount | null;
  issue: string | null;
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
  shared_with: SharedModule[];
}

export interface MethodRowDto {
  code: string;
  label: string;
  is_active: boolean;
  account: PostingAccountDto | null;
  issue: string | null;
}

export interface CategoryRowDto {
  classification_id: string;
  name: string;
  is_active: boolean;
  account: PostingAccountDto | null;
  issue: string | null;
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
  sharedWith: dto.shared_with,
});

export const toCategoryRow = (dto: CategoryRowDto): CategoryRow => ({
  classificationId: dto.classification_id,
  name: dto.name,
  isActive: dto.is_active,
  account: account(dto.account),
  issue: dto.issue,
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
    })),
    categories: dto.categories.map(toCategoryRow),
  };
}

/** Nombre mostrable de una cuenta: «código · nombre» (o solo el nombre si no tiene código). */
export const accountLabel = (a: { code?: string | null; name: string }): string => (a.code ? `${a.code} · ${a.name}` : a.name);
