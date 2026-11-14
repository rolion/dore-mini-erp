import { tr } from '../../../core/i18n/translate';
import { EntryOrigin } from './entry';

export const REGULARIZATION_STATUSES = [
  'missing', 'created', 'existing', 'pending', 'conflict', 'destination_difference', 'invalid', 'failed',
] as const;
export type RegularizationStatus = (typeof REGULARIZATION_STATUSES)[number];

/** Regla de mapeo que escribe la persona: ningún campo se precarga ni se infiere. */
export interface RuleDraft {
  method: string;
  accountId: string;
  from: string;
  to: string;
}

export interface RegularizationInput {
  dateFrom: string;
  dateTo: string;
  rules: RuleDraft[];
}

export interface RegularizationRequest {
  date_from: string | null;
  date_to: string | null;
  mapping: Record<string, { account_id: string; from?: string; to?: string }[]>;
}

export interface SummaryGroup {
  status: RegularizationStatus;
  origin: EntryOrigin;
  accountId: string | null;
  account: string | null;
  currency: string;
  count: number;
  amount: string;
}

export interface SummaryDetail {
  status: string;
  outcome: string;
  origin: EntryOrigin;
  paymentId: string;
  documentRef: string;
  paymentDate: string;
  method: string;
  amount: string;
  reason: string;
  fields: string[];
  error: string;
}

export interface RegularizationSummary {
  mode: 'preview' | 'apply';
  totalPayments: number;
  groups: SummaryGroup[];
  absentFields: Record<string, number>;
  details: SummaryDetail[];
}

export interface SummaryDto {
  mode: 'preview' | 'apply';
  total_payments: number;
  groups: { status: RegularizationStatus; origin: EntryOrigin; account_id: string | null; account: string | null; currency: string; count: number; amount: string }[];
  absent_fields: Record<string, number>;
  details: { status: string; outcome: string; origin: EntryOrigin; payment_id: string; document_ref: string; payment_date: string; method: string; amount: string; reason: string; fields: string[]; error: string }[];
}

export function toSummary(dto: SummaryDto): RegularizationSummary {
  return {
    mode: dto.mode,
    totalPayments: dto.total_payments,
    groups: dto.groups.map((g) => ({ status: g.status, origin: g.origin, accountId: g.account_id, account: g.account, currency: g.currency, count: g.count, amount: g.amount })),
    absentFields: dto.absent_fields,
    details: dto.details.map((d) => ({ status: d.status, outcome: d.outcome, origin: d.origin, paymentId: d.payment_id, documentRef: d.document_ref, paymentDate: d.payment_date, method: d.method, amount: d.amount, reason: d.reason, fields: d.fields, error: d.error })),
  };
}

/** Cuerpo de la petición: una regla vacía (sin método o sin cuenta) no se envía. */
export function toRequest(input: RegularizationInput): RegularizationRequest {
  const mapping: RegularizationRequest['mapping'] = {};
  for (const rule of input.rules) {
    if (!rule.method || !rule.accountId) {
      continue;
    }
    mapping[rule.method] = [
      ...(mapping[rule.method] ?? []),
      { account_id: rule.accountId, ...(rule.from ? { from: rule.from } : {}), ...(rule.to ? { to: rule.to } : {}) },
    ];
  }
  return { date_from: input.dateFrom || null, date_to: input.dateTo || null, mapping };
}

export function statusCount(summary: RegularizationSummary, status: RegularizationStatus): number {
  return summary.groups.filter((g) => g.status === status).reduce((total, g) => total + g.count, 0);
}

/** Importe de un estado por moneda (nunca se suman monedas distintas). */
export function statusAmounts(summary: RegularizationSummary, status: RegularizationStatus): { currency: string; amount: string }[] {
  const totals = new Map<string, number>();
  for (const group of summary.groups.filter((g) => g.status === status)) {
    totals.set(group.currency, Math.round(((totals.get(group.currency) ?? 0) + Number(group.amount)) * 100) / 100);
  }
  return [...totals].map(([currency, amount]) => ({ currency, amount: amount.toFixed(2) }));
}

export function statusLabel(status: string): string {
  return tr(`ACCOUNTING.REGULARIZATION.STATUS.${status.toUpperCase()}`);
}

export function reasonLabel(detail: SummaryDetail): string {
  if (detail.error) {
    return detail.error;
  }
  if (detail.fields.length) {
    return tr('ACCOUNTING.REGULARIZATION.DIFIERE', {
      fields: detail.fields.map((f) => tr(`ACCOUNTING.REGULARIZATION.CAMPO.${f.toUpperCase()}`)).join(', '),
    });
  }
  return detail.reason ? tr(`ACCOUNTING.REGULARIZATION.MOTIVO.${detail.reason.toUpperCase()}`) : '';
}

export class RegularizationError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly messages: string[] = [],
    readonly code: string | null = null,
  ) {
    super(message);
    this.name = 'RegularizationError';
  }
}

function flatten(body: unknown): string[] {
  if (typeof body === 'string') {
    return [body];
  }
  if (Array.isArray(body)) {
    return body.flatMap(flatten);
  }
  if (body && typeof body === 'object') {
    return Object.values(body as Record<string, unknown>).flatMap(flatten);
  }
  return [];
}

export function toRegularizationError(status: number, body: unknown): RegularizationError {
  if (status === 0) {
    return new RegularizationError(tr('CUSTOMERS.CUSTOMERS_API_SERVICE.NO_SE_PUDO_CONECTAR_CON'), 0);
  }
  if (status === 400) {
    return new RegularizationError(tr('ACCOUNTING.REGULARIZATION.REVISA'), 400, flatten(body));
  }
  const record = (body && typeof body === 'object' ? body : {}) as { detail?: unknown; code?: unknown };
  const code = typeof record.code === 'string' ? record.code : null;
  if (status === 409 && code === 'regularization_in_progress') {
    return new RegularizationError(tr('ACCOUNTING.REGULARIZATION.EN_CURSO'), 409, [], code);
  }
  return new RegularizationError(tr('CUSTOMERS.CUSTOMERS_API_SERVICE.OCURRIO_UN_ERROR_INESPERADO_INTENTALO'), status, [], code);
}
