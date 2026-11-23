/** Reporte de ingresos y egresos por mes de un período fiscal. Importes como texto decimal (nunca float). */
export interface IncomeExpenseMonth {
  /** `yyyy-MM`. */
  month: string;
  income: string;
  expense: string;
  profit: string;
}

export interface IncomeExpenseTotals {
  income: string;
  expense: string;
  profit: string;
}

export interface IncomeExpensePeriod {
  id: string;
  name: string;
  dateFrom: string;
  dateTo: string;
  status: 'OPEN' | 'CLOSED';
}

export interface IncomeExpenseReport {
  /** `null` si la empresa no tiene períodos fiscales. */
  period: IncomeExpensePeriod | null;
  months: IncomeExpenseMonth[];
  totals: IncomeExpenseTotals;
}

export interface IncomeExpenseFilters {
  /** Vacío = período por defecto del servidor. */
  periodId: string;
  /** `yyyy-MM`; vacío = todos los meses. */
  months: string[];
}

export interface IncomeExpenseReportDto {
  period: { id: string; name: string; date_from: string; date_to: string; status: 'OPEN' | 'CLOSED' } | null;
  months: IncomeExpenseMonth[];
  totals: IncomeExpenseTotals;
}

export function toIncomeExpenseReport(dto: IncomeExpenseReportDto): IncomeExpenseReport {
  return {
    period: dto.period
      ? { id: dto.period.id, name: dto.period.name, dateFrom: dto.period.date_from, dateTo: dto.period.date_to, status: dto.period.status }
      : null,
    months: dto.months.map((m) => ({ ...m })),
    totals: { ...dto.totals },
  };
}

export type IncomeExpenseSortKey = 'month' | 'income' | 'expense' | 'profit';
export type SortDirection = 'asc' | 'desc';

export interface IncomeExpenseSort {
  key: IncomeExpenseSortKey;
  direction: SortDirection;
}

/** Primer clic en una columna: de mayor a menor; otro clic en la misma: invierte. */
export function nextSort(current: IncomeExpenseSort | null, key: IncomeExpenseSortKey): IncomeExpenseSort {
  if (current?.key === key) return { key, direction: current.direction === 'desc' ? 'asc' : 'desc' };
  return { key, direction: 'desc' };
}

/** Centavos de un importe decimal en texto (`"-400.00"` → -40000n), sin pasar por float. */
function cents(value: string): bigint {
  const negative = value.startsWith('-');
  const [whole, fraction = ''] = value.replace('-', '').split('.');
  const amount = BigInt(whole + fraction.padEnd(2, '0').slice(0, 2));
  return negative ? -amount : amount;
}

export function sortMonths(rows: IncomeExpenseMonth[], sort: IncomeExpenseSort | null): IncomeExpenseMonth[] {
  if (!sort) return rows;
  const sign = sort.direction === 'desc' ? -1 : 1;
  return [...rows].sort((a, b) => {
    if (sort.key === 'month') return sign * a.month.localeCompare(b.month);
    const diff = cents(a[sort.key]) - cents(b[sort.key]);
    return diff === 0n ? a.month.localeCompare(b.month) : sign * (diff < 0n ? -1 : 1);
  });
}

export function isLoss(profit: string): boolean {
  return profit.startsWith('-');
}

/** Meses `yyyy-MM` que intersectan `[dateFrom, dateTo]` (fechas `yyyy-MM-dd`). */
export function monthKeysBetween(dateFrom: string, dateTo: string): string[] {
  const keys: string[] = [];
  let year = Number(dateFrom.slice(0, 4));
  let month = Number(dateFrom.slice(5, 7));
  const endYear = Number(dateTo.slice(0, 4));
  const endMonth = Number(dateTo.slice(5, 7));
  while (year < endYear || (year === endYear && month <= endMonth)) {
    keys.push(`${year}-${String(month).padStart(2, '0')}`);
    month += 1;
    if (month > 12) {
      month = 1;
      year += 1;
    }
  }
  return keys;
}
