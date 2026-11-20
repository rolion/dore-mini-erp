import { IncomeExpenseMonth, monthKeysBetween, nextSort, sortMonths, toIncomeExpenseReport } from './income-expense';
import { makeIncomeExpenseDto } from '../testing/income-expense-fixtures';

describe('income-expense model', () => {
  const rows: IncomeExpenseMonth[] = toIncomeExpenseReport(makeIncomeExpenseDto()).months;

  it('maps the DTO (AC-01)', () => {
    const report = toIncomeExpenseReport(makeIncomeExpenseDto());
    expect(report.period?.dateFrom).toBe('2026-01-01');
    expect(report.totals.profit).toBe('350.00');
  });

  it('first click sorts from highest to lowest, the next one inverts (AC-06)', () => {
    const first = nextSort(null, 'income');
    expect(first).toEqual({ key: 'income', direction: 'desc' });
    expect(nextSort(first, 'income').direction).toBe('asc');
    expect(nextSort(first, 'expense')).toEqual({ key: 'expense', direction: 'desc' });
  });

  it('sorts by amount including negatives, without float math (AC-06)', () => {
    expect(sortMonths(rows, { key: 'profit', direction: 'desc' }).map((r) => r.month)).toEqual(['2026-01', '2026-03', '2026-02']);
    expect(sortMonths(rows, { key: 'profit', direction: 'asc' }).map((r) => r.month)).toEqual(['2026-02', '2026-03', '2026-01']);
    expect(sortMonths(rows, { key: 'month', direction: 'desc' }).map((r) => r.month)).toEqual(['2026-03', '2026-02', '2026-01']);
    expect(sortMonths(rows, null)).toBe(rows);
  });

  it('lists the months a period spans, across years', () => {
    expect(monthKeysBetween('2026-11-15', '2027-01-10')).toEqual(['2026-11', '2026-12', '2027-01']);
  });
});
