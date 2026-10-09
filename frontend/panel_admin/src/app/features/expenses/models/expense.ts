export type PaymentMethod = 'CASH' | 'QR' | 'BANK_TRANSFER' | 'CARD' | 'OTHER';
export type ExpenseStatus = 'ACTIVE' | 'VOIDED';
/** Filtro de estado de la lista: vigentes (por omisión), anulados o todos. */
export type ExpenseStatusFilter = 'active' | 'voided' | 'all';

export const PAYMENT_METHODS: readonly PaymentMethod[] = ['CASH', 'QR', 'BANK_TRANSFER', 'CARD', 'OTHER'];

export const PAYMENT_METHOD_LABELS: Record<PaymentMethod, string> = {
  CASH: 'Efectivo',
  QR: 'QR',
  BANK_TRANSFER: 'Transferencia',
  CARD: 'Tarjeta',
  OTHER: 'Otro',
};

export const EXPENSE_STATUS_LABELS: Record<ExpenseStatus, string> = {
  ACTIVE: 'Vigente',
  VOIDED: 'Anulado',
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
