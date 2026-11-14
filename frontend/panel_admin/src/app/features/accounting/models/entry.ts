import { tr } from '../../../core/i18n/translate';

export type EntryOrigin = 'PRODUCT' | 'SERVICE';
export const ENTRY_ORIGINS: readonly EntryOrigin[] = ['PRODUCT', 'SERVICE'];

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
}

export interface CurrencyTotalDto {
  currency: string;
  count: number;
  amount: string;
  by_origin: Record<EntryOrigin, string>;
}

export interface CurrencyTotal {
  currency: string;
  count: number;
  amount: string;
  byOrigin: Record<EntryOrigin, string>;
}

export interface EntryPageDto {
  count: number;
  results: EntryDto[];
  totals: CurrencyTotalDto[];
  period: { date_from: string | null; date_to: string | null };
  coverage: { first_payment_date: string | null; last_payment_date: string | null; first_recorded_at: string | null };
}

export interface EntryPage {
  count: number;
  results: Entry[];
  totals: CurrencyTotal[];
  coverage: { firstPaymentDate: string | null; lastPaymentDate: string | null; firstRecordedAt: string | null };
}

export interface EntryListFilters {
  dateFrom: string;
  dateTo: string;
  accountId: string;
  method: string;
  origin: EntryOrigin | '';
}

export const EMPTY_ENTRY_FILTERS: EntryListFilters = { dateFrom: '', dateTo: '', accountId: '', method: '', origin: '' };

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
  };
}

export function toEntryPage(dto: EntryPageDto): EntryPage {
  return {
    count: dto.count,
    results: dto.results.map(toEntry),
    totals: dto.totals.map((t) => ({ currency: t.currency, count: t.count, amount: t.amount, byOrigin: t.by_origin })),
    coverage: {
      firstPaymentDate: dto.coverage.first_payment_date,
      lastPaymentDate: dto.coverage.last_payment_date,
      firstRecordedAt: dto.coverage.first_recorded_at,
    },
  };
}

export const ORIGIN_CLASSES: Readonly<Record<EntryOrigin, string>> = { PRODUCT: 'col-blue', SERVICE: 'col-green' };

export function originLabel(origin: EntryOrigin): string {
  return origin === 'PRODUCT' ? tr('ACCOUNTING.ENTRIES.PRODUCTOS') : tr('ACCOUNTING.ENTRIES.SERVICIOS');
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
  return entry.origin === 'SERVICE' ? (entry.documentRef.split('/')[1] ?? entry.documentRef) : entry.documentRef.slice(0, 8);
}
