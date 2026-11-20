import { tr } from '../../../core/i18n/translate';
import type { PostingIssue } from '../../accounting/models/posting-config';
/** Faltante de configuración contable que impide contabilizar (misma forma que en Contabilidad). */
export type { PostingIssue };

export type PaymentMethod = 'CASH' | 'QR' | 'BANK_TRANSFER' | 'CARD' | 'OTHER';
export type ExpenseStatus = 'ACTIVE' | 'VOIDED';
/** Filtro de estado de la lista: vigentes (por omisión), anulados o todos. */
export type ExpenseStatusFilter = 'active' | 'voided' | 'all';

export const PAYMENT_METHODS: readonly PaymentMethod[] = ['CASH', 'QR', 'BANK_TRANSFER', 'CARD', 'OTHER'];

export const PAYMENT_METHOD_LABELS: Record<PaymentMethod, string> = {
  get CASH() { return tr('EXPENSES.EXPENSE.EFECTIVO'); },
  QR: 'QR',
  get BANK_TRANSFER() { return tr('EXPENSES.EXPENSE.TRANSFERENCIA'); },
  get CARD() { return tr('EXPENSES.EXPENSE.TARJETA'); },
  get OTHER() { return tr('EXPENSES.EXPENSE.OTRO'); },
};

export const EXPENSE_STATUS_LABELS: Record<ExpenseStatus, string> = {
  get ACTIVE() { return tr('EXPENSES.EXPENSE.VIGENTE'); },
  get VOIDED() { return tr('EXPENSES.EXPENSE.ANULADO'); },
};

export const DESCRIPTION_MAX_LENGTH = 200;
export const SUPPLIER_MAX_LENGTH = 150;
export const NOTES_MAX_LENGTH = 2000;

/** Categoría embebida en un gasto; `active` permite marcar "(inactiva)" sin otra consulta. */
export interface CategoryRef {
  id: string;
  name: string;
  active: boolean;
}

/** Cuenta contable usada en el asiento del gasto (`active` permite avisar si hoy está deshabilitada). */
export interface AccountRef {
  id: string;
  code: string | null;
  name: string;
  active: boolean;
}

export interface Expense {
  id: string;
  description: string;
  /** Texto decimal ("120.50"); no se opera con aritmética de coma flotante. */
  amount: string;
  /** Fecha del gasto (`AAAA-MM-DD`). */
  expenseDate: string;
  category: CategoryRef;
  paymentMethod: PaymentMethod;
  supplierName: string;
  notes: string;
  status: ExpenseStatus;
  voidedAt: string | null;
  /** Clasificación de egreso aplicada al registrar; `null` en gastos anteriores a CONT-03. */
  classification?: { id: string; name: string; active: boolean } | null;
  /** `true` si generó asiento: monto, categoría, fecha, método y cuentas ya no se editan (se anula y se registra de nuevo). */
  posted: boolean;
  expenseAccount: AccountRef | null;
  paymentAccount: AccountRef | null;
  /** Asiento del gasto (solo en el detalle); enlaza a la pantalla de asientos. */
  journalEntryId: string | null;
  /** Reversión del asiento (solo en el detalle de un gasto anulado que se había contabilizado). */
  reversalEntryId: string | null;
  createdAt: string;
  updatedAt: string;
}

/** Datos editables de un gasto; el estado solo cambia con anular. */
export interface ExpenseInput {
  description: string;
  amount: string;
  categoryId: string;
  expenseDate: string;
  paymentMethod: PaymentMethod;
  supplierName: string;
  notes: string;
}

/** Alta: además, las cuentas elegidas (vacías = las de la configuración) y la clave de idempotencia del envío. */
export interface ExpenseCreateInput extends ExpenseInput {
  expenseAccountId?: string | null;
  paymentAccountId?: string | null;
  idempotencyKey?: string;
}

/** Cuentas por defecto y elegibles para contabilizar un gasto con esa fecha, categoría y método. */
export interface PostingOptions {
  covered: boolean;
  reason: string | null;
  expenseAccount: AccountRef | null;
  paymentAccount: AccountRef | null;
  issues: PostingIssue[];
  expenseAccounts: AccountRef[];
  paymentAccounts: AccountRef[];
}

export interface PostingOptionsDto {
  covered: boolean;
  reason: string | null;
  expense_account: AccountRef | null;
  payment_account: AccountRef | null;
  issues: PostingIssue[];
  expense_accounts: AccountRef[];
  payment_accounts: AccountRef[];
}

/** Forma de respuesta de la API (snake_case). */
export interface ExpenseDto {
  id: string;
  description: string;
  amount: string;
  expense_date: string;
  category: CategoryRef;
  payment_method: PaymentMethod;
  supplier_name: string;
  notes?: string;
  status: ExpenseStatus;
  voided_at: string | null;
  classification?: { id: string; name: string; active: boolean } | null;
  posted?: boolean;
  expense_account?: AccountRef | null;
  payment_account?: AccountRef | null;
  journal_entry_id?: string | null;
  reversal_entry_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExpenseListParams {
  dateFrom?: string;
  dateTo?: string;
  categoryId?: string;
  status?: ExpenseStatusFilter;
  /** Página base 1. */
  page?: number;
  pageSize?: number;
}

export function isVoided(expense: Expense): boolean {
  return expense.status === 'VOIDED';
}
