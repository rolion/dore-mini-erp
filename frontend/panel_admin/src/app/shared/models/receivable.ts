import { tr } from '../../core/i18n/translate';

export type SourceKind = 'quotation' | 'dental';
export type PaymentStatus = 'pending' | 'partial' | 'paid';
export type PaymentMethod = 'CASH' | 'QR' | 'BANK_TRANSFER' | 'CARD' | 'OTHER';
export type LineDecision = 'pending' | 'accepted' | 'rejected';

export const PAYMENT_STATUSES: PaymentStatus[] = ['pending', 'partial', 'paid'];
export const PAYMENT_METHODS: PaymentMethod[] = ['CASH', 'QR', 'BANK_TRANSFER', 'CARD', 'OTHER'];
export const REFERENCE_MAX_LENGTH = 100;

export const STATUS_CLASSES: Record<PaymentStatus, string> = {
  pending: 'col-orange',
  partial: 'col-blue',
  paid: 'col-green',
};

/** Se evalúan al usarlas (no en constantes de módulo): el catálogo de traducciones se carga al arrancar. */
export function statusLabel(status: PaymentStatus): string {
  return tr(`RECEIVABLES.ESTADO_${status.toUpperCase()}`);
}

export function methodLabel(method: PaymentMethod): string {
  return tr(`RECEIVABLES.METODO_${method}`);
}

export interface ObligationSummary {
  kind: SourceKind;
  number: string;
  version: number;
  customer_id: string;
  customer_name: string;
  accepted: string;
  paid: string;
  balance: string;
  payment_status: PaymentStatus;
  created_at: string | null;
  last_payment_date: string | null;
}

export interface ObligationFilters {
  customer_id?: string;
  status?: PaymentStatus | '';
  date_from?: string;
  date_to?: string;
  page?: number;
}

export interface CommitmentLine {
  line_id: string;
  description: string;
  piece: string;
  decision: LineDecision;
  proposed: string;
  accepted: string;
  paid: string;
  balance: string;
  collectible: boolean;
}

export interface CommitmentTotals {
  proposed: string;
  accepted: string;
  pending: string;
  rejected: string;
  paid: string;
  balance: string;
}

export interface CollectionPayment {
  id: string;
  receipt_number: string;
  amount: string;
  payment_method: PaymentMethod;
  payment_date: string;
  reference: string;
  recorded_by_name: string;
  created_at: string | null;
  allocations: { description: string; amount: string }[];
}

export interface Commitment {
  kind: SourceKind;
  number: string;
  version: number;
  status: string;
  customer_id: string;
  /** Id de la versión vigente de la proforma (para volver a ella); `null` si el servidor no lo informa. */
  proforma_id: string | null;
  customer_name: string;
  date: string;
  currency: string;
  payment_status: PaymentStatus;
  totals: CommitmentTotals;
  lines: CommitmentLine[];
  payments: CollectionPayment[];
  allowed_actions: 'register_payment'[];
}

export interface PaymentRegistered extends Commitment {
  payment: CollectionPayment;
  replayed: boolean;
}

export interface PaymentInput {
  idempotency_key: string;
  amount: string;
  payment_method: PaymentMethod;
  payment_date: string | null;
  reference: string;
  allocations: { line_id: string; amount: string }[];
}

export interface ReceivableFailure {
  message: string;
  fields: Record<string, string>;
  conflict: boolean;
}

/** Fecha de hoy en la zona horaria del navegador (AAAA-MM-DD); `toISOString` daría el día UTC. */
export function localToday(now: Date = new Date()): string {
  const pad = (n: number): string => String(n).padStart(2, '0');
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

/** Importes en centavos enteros: evita errores de coma flotante al sumar y comparar. */
export function toCents(value: string | null | undefined): number | null {
  const text = (value ?? '').trim().replace(',', '.');
  if (!/^\d{1,10}(\.\d{1,2})?$/.test(text)) return null;
  const [whole, decimals = ''] = text.split('.');
  return Number(whole) * 100 + Number(decimals.padEnd(2, '0'));
}

export function fromCents(cents: number): string {
  const sign = cents < 0 ? '-' : '';
  const abs = Math.abs(cents);
  return `${sign}${Math.floor(abs / 100)}.${String(abs % 100).padStart(2, '0')}`;
}
