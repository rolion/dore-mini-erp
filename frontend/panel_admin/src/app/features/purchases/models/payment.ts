import { tr } from '../../../core/i18n/translate';
export type PaymentMethod = 'CASH' | 'QR' | 'BANK_TRANSFER' | 'CARD' | 'OTHER';
export type PaymentRecordStatus = 'confirmed' | 'voided';

export const PAYMENT_METHOD_LABELS: Readonly<Record<PaymentMethod, string>> = {
  get CASH() { return tr('EXPENSES.EXPENSE.EFECTIVO'); },
  QR: 'QR',
  get BANK_TRANSFER() { return tr('EXPENSES.EXPENSE.TRANSFERENCIA'); },
  get CARD() { return tr('EXPENSES.EXPENSE.TARJETA'); },
  get OTHER() { return tr('EXPENSES.EXPENSE.OTRO'); },
};

export const PAYMENT_METHODS: readonly PaymentMethod[] = ['CASH', 'QR', 'BANK_TRANSFER', 'CARD', 'OTHER'];

export const PAYMENT_STATUS_RECORD_LABELS: Readonly<Record<PaymentRecordStatus, string>> = {
  get confirmed() { return tr('INVENTORY.MOVEMENT.CONFIRMADO'); },
  get voided() { return tr('EXPENSES.EXPENSE.ANULADO'); },
};

/** Asiento de un pago: `debt` liquida deuda reconocida; `advance` es un anticipo a proveedores. */
export interface PaymentAccountingEntry {
  id: string;
  kind: 'debt' | 'advance';
  accountingDate: string;
  total: string;
}

/** Un faltante de configuración contable que impide registrar el pago (409 `posting_configuration_missing`). */
export interface PaymentPostingIssue {
  code: string;
  subject: string;
  message: string;
}

export interface PaymentPreviewLine {
  side: 'DEBIT' | 'CREDIT';
  role: string;
  accountName: string;
  amount: string;
}

/** Asiento previsto de un pago (no escribe nada): reparto, líneas y faltantes. */
export interface PaymentPreview {
  covered: boolean;
  debtAmount: string;
  advanceAmount: string;
  lines: PaymentPreviewLine[];
  issues: PaymentPostingIssue[];
}

export interface PaymentPreviewDto {
  covered: boolean;
  debt_amount: string;
  advance_amount: string;
  lines: { side: 'DEBIT' | 'CREDIT'; role: string; account: { name: string }; amount: string }[];
  issues: { code?: string; subject?: string; message: string }[];
}

export interface Payment {
  id: string;
  /** Referencia interna provisional (`PAG-XXXXXXXX`). */
  reference: string;
  /** Texto decimal con 2 decimales. */
  amount: string;
  paymentMethod: PaymentMethod;
  paymentDate: string;
  status: PaymentRecordStatus;
  userName: string;
  createdAt: string;
  /** Parte que liquida deuda reconocida y parte que es anticipo (`debt + advance = amount`). */
  debtAmount: string;
  advanceAmount: string;
  /** Asientos del pago (0-2); vacío sin Contabilidad o sin cobertura. */
  accountingEntries: PaymentAccountingEntry[];
}

/** Lo que se envía al registrar; `paymentId` se genera al abrir el diálogo y se reutiliza en cada reintento. */
export interface PaymentInput {
  paymentId: string;
  amount: string;
  paymentMethod: PaymentMethod;
  paymentDate: string;
}

/** Forma de respuesta de la API (snake_case). */
export interface PaymentDto {
  id: string;
  reference: string;
  amount: string;
  payment_method: PaymentMethod;
  payment_date: string;
  status: PaymentRecordStatus;
  user_name: string;
  created_at: string;
  debt_amount?: string;
  advance_amount?: string;
  accounting_entries?: { id: string; kind: 'debt' | 'advance'; accounting_date: string; total: string }[];
}

export interface PaymentFieldErrors {
  amount?: string;
  paymentMethod?: string;
  paymentDate?: string;
}

export class PaymentApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly fieldErrors: PaymentFieldErrors = {},
    /** Código estable de la API (p. ej. `classification_not_configured`). */
    readonly code: string | null = null,
    /** Faltantes de un 409 `posting_configuration_missing` (vacío en otros conflictos). */
    readonly postingIssues: PaymentPostingIssue[] = [],
  ) {
    super(message);
    this.name = 'PaymentApiError';
  }
}
