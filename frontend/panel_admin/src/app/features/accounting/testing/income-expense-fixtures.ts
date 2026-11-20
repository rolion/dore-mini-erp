import { IncomeExpenseReportDto } from '../models/income-expense';

export function makeIncomeExpenseDto(overrides: Partial<IncomeExpenseReportDto> = {}): IncomeExpenseReportDto {
  return {
    period: { id: 'p-1', name: '2026', date_from: '2026-01-01', date_to: '2026-03-31', status: 'OPEN' },
    months: [
      { month: '2026-01', income: '1000.00', expense: '500.00', profit: '500.00' },
      { month: '2026-02', income: '200.00', expense: '350.00', profit: '-150.00' },
      { month: '2026-03', income: '0.00', expense: '0.00', profit: '0.00' },
    ],
    totals: { income: '1200.00', expense: '850.00', profit: '350.00' },
    ...overrides,
  };
}
