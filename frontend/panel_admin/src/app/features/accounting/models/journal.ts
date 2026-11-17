import { tr } from '../../../core/i18n/translate';
import { AccountingApiError, FieldErrors } from './accounting';

export const JOURNAL_SOURCES = ['MANUAL', 'AUTOMATIC'] as const;
export type JournalSource = (typeof JOURNAL_SOURCES)[number];

export const JOURNAL_DESCRIPTION_MAX = 200;
export const JOURNAL_REASON_MAX = 200;
export const JOURNAL_MEMO_MAX = 200;
export const JOURNAL_MIN_LINES = 2;

export interface JournalFilters {
  dateFrom: string;
  dateTo: string;
  accountId: string;
  source: JournalSource | '';
}

export const EMPTY_JOURNAL_FILTERS: JournalFilters = { dateFrom: '', dateTo: '', accountId: '', source: '' };

export interface JournalOrigin {
  kind: string;
  id?: string;
  /** El servidor declara que el módulo propietario está habilitado. */
  available: boolean;
}

export interface JournalRow {
  id: string;
  accountingDate: string;
  description: string;
  source: JournalSource;
  origin: JournalOrigin | null;
  currency: string;
  /** Decimal en texto (nunca float). */
  total: string;
  createdByName: string;
  createdAt: string;
  isReversal: boolean;
  reversedById: string | null;
}

export interface JournalLine {
  position: number;
  account: { id: string; code: string | null; name: string };
  debit: string;
  credit: string;
  memo: string;
}

export interface JournalEntryDetail extends JournalRow {
  period: { id: string; name: string } | null;
  lines: JournalLine[];
  totalDebit: string;
  totalCredit: string;
  reversesId: string | null;
  reversalReason: string;
  canReverse: boolean;
}

export interface JournalPage {
  count: number;
  results: JournalRow[];
}

export interface JournalRowDto {
  id: string;
  accounting_date: string;
  description: string;
  source: JournalSource;
  origin: JournalOrigin | null;
  currency: string;
  total: string;
  created_by_name: string;
  created_at: string;
  is_reversal: boolean;
  reversed_by_id: string | null;
}

export interface JournalDetailDto extends JournalRowDto {
  period: { id: string; name: string } | null;
  lines: JournalLine[];
  total_debit: string;
  total_credit: string;
  reverses_id: string | null;
  reversal_reason: string;
  can_reverse: boolean;
}

export interface JournalPageDto {
  count: number;
  results: JournalRowDto[];
}

export function toJournalRow(dto: JournalRowDto): JournalRow {
  return {
    id: dto.id,
    accountingDate: dto.accounting_date,
    description: dto.description,
    source: dto.source,
    origin: dto.origin,
    currency: dto.currency,
    total: dto.total,
    createdByName: dto.created_by_name,
    createdAt: dto.created_at,
    isReversal: dto.is_reversal,
    reversedById: dto.reversed_by_id,
  };
}

export function toJournalDetail(dto: JournalDetailDto): JournalEntryDetail {
  return {
    ...toJournalRow(dto),
    period: dto.period,
    lines: dto.lines,
    totalDebit: dto.total_debit,
    totalCredit: dto.total_credit,
    reversesId: dto.reverses_id,
    reversalReason: dto.reversal_reason,
    canReverse: dto.can_reverse,
  };
}

export function toJournalPage(dto: JournalPageDto): JournalPage {
  return { count: dto.count, results: dto.results.map(toJournalRow) };
}

/** Enlace al documento de origen: solo con módulo habilitado y una pantalla de destino conocida. */
export function journalOriginLink(origin: JournalOrigin | null): string[] | null {
  if (!origin || !origin.available || !origin.id) {
    return null;
  }
  return origin.kind === 'PRODUCT' ? ['/pocketbiz/sales/orders', origin.id] : null;
}

export function sourceLabel(source: JournalSource): string {
  return source === 'MANUAL' ? tr('ACCOUNTING.JOURNAL.MANUAL') : tr('ACCOUNTING.JOURNAL.AUTOMATICO');
}

export const SOURCE_CLASSES: Record<JournalSource, string> = { MANUAL: 'col-blue', AUTOMATIC: 'col-grey' };

// --- Formulario: aritmética entera en centavos (replica la regla del servidor; manda el servidor al guardar) ---

/** Línea tal como se escribe en el formulario (importes en texto). */
export interface DraftLine {
  accountId: string;
  debit: string;
  credit: string;
}

export interface JournalDraft {
  accountingDate: string;
  description: string;
  lines: DraftLine[];
}

const AMOUNT_PATTERN = /^\d{1,10}([.,]\d{1,2})?$/;

/** Centavos de un importe escrito (`'200'`, `'200.5'`, `'200,50'`); `0` si está vacío y `null` si no es válido. */
export function parseCents(text: string): number | null {
  const value = text.trim();
  if (value === '') {
    return 0;
  }
  if (!AMOUNT_PATTERN.test(value)) {
    return null;
  }
  const [whole, fraction = ''] = value.replace(',', '.').split('.');
  return Number(whole) * 100 + Number(fraction.padEnd(2, '0'));
}

export function formatCents(cents: number): string {
  const sign = cents < 0 ? '-' : '';
  const abs = Math.abs(cents);
  return `${sign}${Math.floor(abs / 100)}.${String(abs % 100).padStart(2, '0')}`;
}

export interface DraftTotals {
  debit: number;
  credit: number;
  difference: number;
}

export function draftTotals(lines: readonly DraftLine[]): DraftTotals {
  let debit = 0;
  let credit = 0;
  for (const line of lines) {
    debit += parseCents(line.debit) ?? 0;
    credit += parseCents(line.credit) ?? 0;
  }
  return { debit, credit, difference: debit - credit };
}

/** Problema de una línea del borrador (texto listo para mostrar) o `''` si está bien. */
export function lineProblem(line: DraftLine): string {
  const debit = parseCents(line.debit);
  const credit = parseCents(line.credit);
  if (debit === null || credit === null) {
    return tr('ACCOUNTING.JOURNAL.IMPORTE_INVALIDO');
  }
  if (debit > 0 && credit > 0) {
    return tr('ACCOUNTING.JOURNAL.DEBE_O_HABER');
  }
  if (!line.accountId) {
    return tr('ACCOUNTING.JOURNAL.FALTA_CUENTA');
  }
  if (debit === 0 && credit === 0) {
    return tr('ACCOUNTING.JOURNAL.FALTA_IMPORTE');
  }
  return '';
}

/** Motivos por los que aún no se puede confirmar (vacío = se puede). */
export function draftBlockers(draft: JournalDraft): string[] {
  const blockers: string[] = [];
  if (!draft.accountingDate) {
    blockers.push(tr('ACCOUNTING.JOURNAL.FALTA_FECHA'));
  }
  if (!draft.description.trim()) {
    blockers.push(tr('ACCOUNTING.JOURNAL.FALTA_DESCRIPCION'));
  }
  if (draft.lines.length < JOURNAL_MIN_LINES) {
    blockers.push(tr('ACCOUNTING.JOURNAL.MINIMO_DOS_LINEAS'));
  }
  if (draft.lines.some((line) => lineProblem(line) !== '')) {
    blockers.push(tr('ACCOUNTING.JOURNAL.LINEAS_INCOMPLETAS'));
  }
  const accounts = new Set(draft.lines.map((line) => line.accountId).filter((id) => id !== ''));
  if (accounts.size < JOURNAL_MIN_LINES) {
    blockers.push(tr('ACCOUNTING.JOURNAL.DOS_CUENTAS_DISTINTAS'));
  }
  const totals = draftTotals(draft.lines);
  if (totals.difference !== 0) {
    blockers.push(tr('ACCOUNTING.JOURNAL.NO_CUADRA'));
  } else if (totals.debit === 0) {
    blockers.push(tr('ACCOUNTING.JOURNAL.TOTAL_CERO'));
  }
  return blockers;
}

export interface JournalInputBody {
  accounting_date: string;
  description: string;
  lines: { account_id: string; debit?: string; credit?: string; memo?: string }[];
}

export function toJournalBody(draft: JournalDraft): JournalInputBody {
  return {
    accounting_date: draft.accountingDate,
    description: draft.description.trim(),
    lines: draft.lines.map((line) => {
      const debit = parseCents(line.debit) ?? 0;
      return debit > 0
        ? { account_id: line.accountId, debit: formatCents(debit) }
        : { account_id: line.accountId, credit: formatCents(parseCents(line.credit) ?? 0) };
    }),
  };
}

// --- Errores de la API de asientos ---

/** Traduce un error HTTP: los 400 conservan los mensajes por campo del servidor (`lines`, `accounting_date`, …). */
export function toJournalError(status: number, body: unknown): AccountingApiError {
  if (status === 0) {
    return new AccountingApiError(tr('ACCOUNTING.JOURNAL.SIN_CONEXION'), 0);
  }
  const record = (body && typeof body === 'object' ? body : {}) as Record<string, unknown>;
  if (status === 400) {
    const fieldErrors: FieldErrors = {};
    for (const [field, value] of Object.entries(record)) {
      const messages = Array.isArray(value) ? value.map(String) : typeof value === 'string' ? [value] : [];
      if (messages.length) {
        fieldErrors[field] = messages;
      }
    }
    return new AccountingApiError(tr('ACCOUNTING.JOURNAL.REVISA_LOS_DATOS'), 400, fieldErrors);
  }
  if (status === 404) {
    return new AccountingApiError(tr('ACCOUNTING.JOURNAL.NO_ENCONTRADO'), 404);
  }
  const detail = typeof record['detail'] === 'string' ? record['detail'] : '';
  return new AccountingApiError(detail || tr('ACCOUNTING.JOURNAL.ERROR_INESPERADO'), status);
}

export function isRangeInvalid(filters: JournalFilters): boolean {
  return !!filters.dateFrom && !!filters.dateTo && filters.dateFrom > filters.dateTo;
}

export function hasActiveFilters(filters: JournalFilters): boolean {
  return Object.values(filters).some((value) => value !== '');
}
