import { tr } from '../../../core/i18n/translate';

export type EntryOrigin = 'PRODUCT' | 'SERVICE' | 'EXPENSE' | 'PURCHASE_PAYMENT';
export const ENTRY_ORIGINS: readonly EntryOrigin[] = ['PRODUCT', 'SERVICE', 'EXPENSE', 'PURCHASE_PAYMENT'];
/** Orígenes de ingresos: los únicos que desglosa `by_origin` de los totales. */
export type IncomeOrigin = 'PRODUCT' | 'SERVICE';
export type EntryDirection = 'INCOME' | 'EXPENSE';
export const ENTRY_DIRECTIONS: readonly EntryDirection[] = ['INCOME', 'EXPENSE'];
export type EntryOperation = 'RECORD' | 'REVERSAL';

export interface EntryDto {
  id: string;
  account: { id: string; name: string; currency: string };
  currency: string;
  amount: string;
  payment_date: string;
  created_at: string;
  method: string;
  method_label: string;
  recorded_by_name: string;
  origin: { kind: EntryOrigin; label: string };
  source: { id?: string; document_ref: string; receipt_number: string; available: boolean };
  direction?: EntryDirection;
  operation?: EntryOperation;
  classification?: { id: string; name: string } | null;
  reversal_of?: string | null;
  reversed_by?: string | null;
}

export interface Entry {
  id: string;
  accountId: string;
  accountName: string;
  currency: string;
  amount: string;
  paymentDate: string;
  createdAt: string;
  method: string;
  methodLabel: string;
  recordedByName: string;
  origin: EntryOrigin;
  sourceId: string;
  documentRef: string;
  receiptNumber: string;
  sourceAvailable: boolean;
  direction: EntryDirection;
  operation: EntryOperation;
  classificationName: string;
  reversalOf: string | null;
  reversedBy: string | null;
}

export interface CurrencyTotalDto {
  currency: string;
  count: number;
  amount: string;
  by_origin: Record<IncomeOrigin, string>;
  expense?: string;
  by_direction?: { net: string };
}

export interface CurrencyTotal {
  currency: string;
  count: number;
  /** Ingresos originales (cobros). */
  amount: string;
  byOrigin: Record<IncomeOrigin, string>;
  expense: string;
  net: string;
}

export interface EntryPageDto {
  count: number;
  results: EntryDto[];
  totals: CurrencyTotalDto[];
  period: { date_from: string | null; date_to: string | null };
  coverage: {
    first_payment_date: string | null;
    last_payment_date: string | null;
    first_recorded_at: string | null;
    cutoff_date?: string | null;
    gaps?: { from: string; to: string }[];
  };
}

export interface EntryPage {
  count: number;
  results: Entry[];
  totals: CurrencyTotal[];
  coverage: EntryCoverage;
}

export interface EntryCoverage {
  firstPaymentDate: string | null;
  lastPaymentDate: string | null;
  firstRecordedAt: string | null;
  cutoffDate: string | null;
  gaps: { from: string; to: string }[];
}

export interface EntryListFilters {
  dateFrom: string;
  dateTo: string;
  accountId: string;
  method: string;
  origin: EntryOrigin | '';
  direction: EntryDirection | '';
}

export const EMPTY_ENTRY_FILTERS: EntryListFilters = { dateFrom: '', dateTo: '', accountId: '', method: '', origin: '', direction: '' };

export function toEntry(dto: EntryDto): Entry {
  return {
    id: dto.id,
    accountId: dto.account.id,
    accountName: dto.account.name,
    currency: dto.currency,
    amount: dto.amount,
    paymentDate: dto.payment_date,
    createdAt: dto.created_at,
    method: dto.method,
    methodLabel: dto.method_label,
    recordedByName: dto.recorded_by_name,
    origin: dto.origin.kind,
    sourceId: dto.source.id ?? '',
    documentRef: dto.source.document_ref,
    receiptNumber: dto.source.receipt_number,
    sourceAvailable: dto.source.available,
    direction: dto.direction ?? 'INCOME',
    operation: dto.operation ?? 'RECORD',
    classificationName: dto.classification?.name ?? '',
    reversalOf: dto.reversal_of ?? null,
    reversedBy: dto.reversed_by ?? null,
  };
}

export function toEntryPage(dto: EntryPageDto): EntryPage {
  return {
    count: dto.count,
    results: dto.results.map(toEntry),
    totals: dto.totals.map((t) => ({
      currency: t.currency,
      count: t.count,
      amount: t.amount,
      byOrigin: t.by_origin,
      expense: t.expense ?? '0.00',
      net: t.by_direction?.net ?? t.amount,
    })),
    coverage: {
      firstPaymentDate: dto.coverage.first_payment_date,
      lastPaymentDate: dto.coverage.last_payment_date,
      firstRecordedAt: dto.coverage.first_recorded_at,
      cutoffDate: dto.coverage.cutoff_date ?? null,
      gaps: dto.coverage.gaps ?? [],
    },
  };
}

export const ORIGIN_CLASSES: Readonly<Record<EntryOrigin, string>> = {
  PRODUCT: 'col-blue',
  SERVICE: 'col-green',
  EXPENSE: 'col-orange',
  PURCHASE_PAYMENT: 'col-orange',
};

export function originLabel(origin: EntryOrigin): string {
  switch (origin) {
    case 'PRODUCT':
      return tr('ACCOUNTING.ENTRIES.PRODUCTOS');
    case 'SERVICE':
      return tr('ACCOUNTING.ENTRIES.SERVICIOS');
    case 'EXPENSE':
      return tr('ACCOUNTING.ENTRIES.GASTOS');
    case 'PURCHASE_PAYMENT':
      return tr('ACCOUNTING.ENTRIES.PAGOS_DE_COMPRAS');
  }
}

export function directionLabel(direction: EntryDirection): string {
  return direction === 'INCOME' ? tr('ACCOUNTING.ENTRIES.INGRESO') : tr('ACCOUNTING.ENTRIES.EGRESO');
}

/** Importe con signo: los egresos restan dinero de la cuenta (una reversión de egreso lo devuelve). */
export function signedAmount(entry: Entry): string {
  const text = formatAmount(entry.amount, entry.currency);
  return entry.direction === 'EXPENSE' ? `−${text}` : text;
}

/** Importe con su moneda, tal como lo entrega el servidor: nunca se convierte ni se suma entre monedas. */
export function formatAmount(amount: string, currency: string): string {
  return currency === 'BOB' ? tr('SHARED.MONEY_PIPE.BS', { p0: amount }) : `${amount} ${currency}`;
}

/** Enlace al documento de origen, solo si el servidor lo declara disponible y existe una pantalla para él. */
export function sourceLink(entry: Entry): string[] | null {
  if (!entry.sourceAvailable || !entry.documentRef) {
    return null;
  }
  if (entry.origin === 'EXPENSE' || entry.origin === 'PURCHASE_PAYMENT') {
    return null; // sin pantalla de destino hasta que Gastos y Compras registren sus movimientos (GAS-01, COM-01)
  }
  if (entry.origin === 'PRODUCT') {
    return ['/pocketbiz/sales/orders', entry.documentRef];
  }
  const [kind, number] = entry.documentRef.split('/');
  return kind && number ? ['/pocketbiz/receivables', kind, number] : null;
}

/** Texto del documento de origen: para servicios es el número de proforma (`kind/number` → `number`). */
export function documentLabel(entry: Entry): string {
  if (!entry.documentRef) {
    return '—';
  }
  if (entry.origin === 'SERVICE') {
    return entry.documentRef.split('/')[1] ?? entry.documentRef;
  }
  return entry.origin === 'PRODUCT' ? entry.documentRef.slice(0, 8) : entry.documentRef;
}
