/** Filtros del Balance general; las fechas son `yyyy-MM-dd` y vacío significa «sin límite». */
export interface BalanceSheetFilters {
  dateFrom: string;
  dateTo: string;
}

export const EMPTY_BALANCE_SHEET_FILTERS: BalanceSheetFilters = { dateFrom: '', dateTo: '' };

export type BalanceSheetSectionKey = 'ASSET' | 'LIABILITY' | 'EQUITY';

/** Importes en texto decimal (nunca float): saldo inicial, movimiento del rango y saldo final. */
export interface SheetAmounts {
  opening: string;
  movement: string;
  closing: string;
}

export interface SheetRow extends SheetAmounts {
  accountId: string;
  code: string | null;
  name: string;
  isActive: boolean;
}

export interface BalanceSheetSection {
  key: BalanceSheetSectionKey;
  rows: SheetRow[];
  total: SheetAmounts;
  /** Solo Patrimonio: resultado anterior a «Desde» y del período. */
  previousResult: SheetAmounts | null;
  periodResult: SheetAmounts | null;
}

export interface BalanceSheetTotals {
  assets: string;
  liabilities: string;
  equity: string;
  liabilitiesAndEquity: string;
  difference: string;
  balanced: boolean;
  unclassifiedBalance: string;
}

export interface BalanceSheet {
  dateFrom: string | null;
  dateTo: string | null;
  /** Con «Desde» se muestran las columnas Saldo inicial y Movimiento. */
  hasOpening: boolean;
  sections: BalanceSheetSection[];
  totals: BalanceSheetTotals;
}

export interface SheetRowDto extends SheetAmounts {
  account_id: string;
  code: string | null;
  name: string;
  is_active: boolean;
}

export interface BalanceSheetSectionDto {
  key: BalanceSheetSectionKey;
  rows: SheetRowDto[];
  total: SheetAmounts;
  previous_result?: SheetAmounts;
  period_result?: SheetAmounts;
}

export interface BalanceSheetDto {
  date_from: string | null;
  date_to: string | null;
  has_opening: boolean;
  sections: BalanceSheetSectionDto[];
  totals: {
    assets: string;
    liabilities: string;
    equity: string;
    liabilities_and_equity: string;
    difference: string;
    balanced: boolean;
    unclassified_balance: string;
  };
}

export function toBalanceSheet(dto: BalanceSheetDto): BalanceSheet {
  return {
    dateFrom: dto.date_from,
    dateTo: dto.date_to,
    hasOpening: dto.has_opening,
    sections: dto.sections.map((section) => ({
      key: section.key,
      rows: section.rows.map((row) => ({
        accountId: row.account_id,
        code: row.code,
        name: row.name,
        isActive: row.is_active,
        opening: row.opening,
        movement: row.movement,
        closing: row.closing,
      })),
      total: section.total,
      previousResult: section.previous_result ?? null,
      periodResult: section.period_result ?? null,
    })),
    totals: {
      assets: dto.totals.assets,
      liabilities: dto.totals.liabilities,
      equity: dto.totals.equity,
      liabilitiesAndEquity: dto.totals.liabilities_and_equity,
      difference: dto.totals.difference,
      balanced: dto.totals.balanced,
      unclassifiedBalance: dto.totals.unclassified_balance,
    },
  };
}

export function hasActiveBalanceSheetFilters(filters: BalanceSheetFilters): boolean {
  return filters.dateFrom !== '' || filters.dateTo !== '';
}

export function isBalanceSheetRangeInvalid(filters: BalanceSheetFilters): boolean {
  return !!filters.dateFrom && !!filters.dateTo && filters.dateFrom > filters.dateTo;
}

/** Texto decimal del servidor sin valor (`0`, `0.00`, `-0.00`). */
export function isZeroAmount(value: string): boolean {
  return /^-?0+(\.0+)?$/.test(value);
}

export function isNegativeAmount(value: string): boolean {
  return value.startsWith('-') && !isZeroAmount(value);
}

/** Sin cuentas con saldo en ninguna sección y sin resultado: nada que mostrar. */
export function isBalanceSheetEmpty(sheet: BalanceSheet): boolean {
  return sheet.sections.every((section) => section.rows.length === 0)
    && isZeroAmount(sheet.totals.equity) && isZeroAmount(sheet.totals.assets) && isZeroAmount(sheet.totals.liabilities);
}
