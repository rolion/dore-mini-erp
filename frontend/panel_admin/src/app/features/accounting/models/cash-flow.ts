import { JournalOrigin } from './journal';

export const MOVEMENT_TYPES = ['inflow', 'outflow', 'transfer'] as const;
export type MovementType = (typeof MOVEMENT_TYPES)[number];
export type MovementKind = 'inflow' | 'outflow' | 'transfer_in' | 'transfer_out';

export interface CashFlowFilters {
  dateFrom: string;
  dateTo: string;
  accountId: string;
  type: MovementType | '';
}

/** Importes siempre como texto decimal del servidor (nunca float). */
export interface CashFlowSummary {
  opening: string;
  inflow: string;
  outflow: string;
  net: string;
  closing: string;
  transfers: string;
}

export interface CashFlowAccount {
  accountId: string;
  name: string;
  opening: string;
  inflow: string;
  outflow: string;
  transfersIn: string;
  transfersOut: string;
  net: string;
  closing: string;
}

export interface CashFlow {
  dateFrom: string;
  dateTo: string;
  cutoffDate: string | null;
  partial: boolean;
  summary: CashFlowSummary;
  accounts: CashFlowAccount[];
}

export interface CashFlowMovement {
  entryId: string;
  accountingDate: string;
  accountId: string;
  accountName: string;
  description: string;
  origin: JournalOrigin | null;
  kind: MovementKind;
  amount: string;
  isReversal: boolean;
}

export interface MovementTotals {
  inflow: string;
  outflow: string;
  transfersIn: string;
  transfersOut: string;
}

export interface CashFlowMovementPage {
  count: number;
  totals: MovementTotals;
  results: CashFlowMovement[];
}

export interface CashFlowDto {
  period: { date_from: string; date_to: string };
  coverage: { cutoff_date: string | null; partial: boolean };
  summary: CashFlowSummary;
  accounts: {
    account_id: string;
    name: string;
    opening: string;
    inflow: string;
    outflow: string;
    transfers_in: string;
    transfers_out: string;
    net: string;
    closing: string;
  }[];
}

export interface CashFlowMovementPageDto {
  count: number;
  totals: { inflow: string; outflow: string; transfers_in: string; transfers_out: string };
  results: {
    entry_id: string;
    accounting_date: string;
    account: { id: string; name: string };
    description: string;
    origin: JournalOrigin | null;
    kind: MovementKind;
    amount: string;
    is_reversal: boolean;
  }[];
}

export function toCashFlow(dto: CashFlowDto): CashFlow {
  return {
    dateFrom: dto.period.date_from,
    dateTo: dto.period.date_to,
    cutoffDate: dto.coverage.cutoff_date,
    partial: dto.coverage.partial,
    summary: dto.summary,
    accounts: dto.accounts.map((a) => ({
      accountId: a.account_id,
      name: a.name,
      opening: a.opening,
      inflow: a.inflow,
      outflow: a.outflow,
      transfersIn: a.transfers_in,
      transfersOut: a.transfers_out,
      net: a.net,
      closing: a.closing,
    })),
  };
}

export function toCashFlowMovementPage(dto: CashFlowMovementPageDto): CashFlowMovementPage {
  return {
    count: dto.count,
    totals: {
      inflow: dto.totals.inflow,
      outflow: dto.totals.outflow,
      transfersIn: dto.totals.transfers_in,
      transfersOut: dto.totals.transfers_out,
    },
    results: dto.results.map((r) => ({
      entryId: r.entry_id,
      accountingDate: r.accounting_date,
      accountId: r.account.id,
      accountName: r.account.name,
      description: r.description,
      origin: r.origin,
      kind: r.kind,
      amount: r.amount,
      isReversal: r.is_reversal,
    })),
  };
}

export function isCashFlowRangeInvalid(filters: Pick<CashFlowFilters, 'dateFrom' | 'dateTo'>): boolean {
  return !filters.dateFrom || !filters.dateTo || filters.dateFrom > filters.dateTo;
}

/** Mes en curso (`AAAA-MM-DD`), por defecto de la página cuando la URL no trae fechas. */
export function currentMonthRange(today = new Date()): { dateFrom: string; dateTo: string } {
  const pad = (n: number): string => String(n).padStart(2, '0');
  const first = `${today.getFullYear()}-${pad(today.getMonth() + 1)}-01`;
  const last = new Date(today.getFullYear(), today.getMonth() + 1, 0).getDate();
  return { dateFrom: first, dateTo: `${today.getFullYear()}-${pad(today.getMonth() + 1)}-${pad(last)}` };
}
