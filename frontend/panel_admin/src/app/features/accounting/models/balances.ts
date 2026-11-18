import { AccountClassCode } from './accounting';

/** Filtros de Saldos; las fechas son `yyyy-MM-dd` y vacío significa «sin límite». */
export interface BalanceFilters {
  dateFrom: string;
  dateTo: string;
  accountClass: AccountClassCode | '';
  accountId: string;
}

export const EMPTY_BALANCE_FILTERS: BalanceFilters = { dateFrom: '', dateTo: '', accountClass: '', accountId: '' };

/** Cifras de una cuenta o de los totales; decimales en texto (nunca float). */
export interface BalanceAmounts {
  openingDebitBalance: string;
  openingCreditBalance: string;
  debit: string;
  credit: string;
  debitBalance: string;
  creditBalance: string;
}

export interface BalanceRow extends BalanceAmounts {
  accountId: string;
  code: string | null;
  name: string;
  accountClass: AccountClassCode | null;
  isActive: boolean;
}

export interface BalanceTotals extends BalanceAmounts {
  balanced: boolean;
}

export interface Balances {
  dateFrom: string | null;
  dateTo: string | null;
  /** Con «Desde» el servidor informa saldo inicial anterior al rango. */
  hasOpening: boolean;
  rows: BalanceRow[];
  totals: BalanceTotals;
}

interface AmountsDto {
  opening_debit_balance: string;
  opening_credit_balance: string;
  debit: string;
  credit: string;
  debit_balance: string;
  credit_balance: string;
}

export interface BalanceRowDto extends AmountsDto {
  account_id: string;
  code: string | null;
  name: string;
  account_class: AccountClassCode | null;
  is_active: boolean;
}

export interface BalancesDto {
  date_from: string | null;
  date_to: string | null;
  has_opening: boolean;
  rows: BalanceRowDto[];
  totals: AmountsDto & { balanced: boolean };
}

function toAmounts(dto: AmountsDto): BalanceAmounts {
  return {
    openingDebitBalance: dto.opening_debit_balance,
    openingCreditBalance: dto.opening_credit_balance,
    debit: dto.debit,
    credit: dto.credit,
    debitBalance: dto.debit_balance,
    creditBalance: dto.credit_balance,
  };
}

export function toBalances(dto: BalancesDto): Balances {
  return {
    dateFrom: dto.date_from,
    dateTo: dto.date_to,
    hasOpening: dto.has_opening,
    rows: dto.rows.map((row) => ({
      ...toAmounts(row),
      accountId: row.account_id,
      code: row.code,
      name: row.name,
      accountClass: row.account_class,
      isActive: row.is_active,
    })),
    totals: { ...toAmounts(dto.totals), balanced: dto.totals.balanced },
  };
}

export function hasActiveBalanceFilters(filters: BalanceFilters): boolean {
  return Object.values(filters).some((value) => value !== '');
}

export function isBalanceRangeInvalid(filters: BalanceFilters): boolean {
  return !!filters.dateFrom && !!filters.dateTo && filters.dateFrom > filters.dateTo;
}
