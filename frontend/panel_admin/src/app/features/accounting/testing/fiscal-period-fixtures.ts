import { FiscalPeriod } from '../models/fiscal-period';

export function fiscalPeriod(overrides: Partial<FiscalPeriod> = {}): FiscalPeriod {
  return {
    id: 'p1',
    name: 'Año 2026',
    startDate: '2026-01-01',
    endDate: '2026-12-31',
    status: 'OPEN',
    isOpen: true,
    closedByName: '',
    ...overrides,
  };
}
