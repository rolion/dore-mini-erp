import { monthRange, toIsoDate } from './date-range';

describe('date-range', () => {
  it('formats a local date without shifting the day', () => {
    expect(toIsoDate(new Date(2026, 9, 5, 23, 59))).toBe('2026-10-05');
    expect(toIsoDate(new Date(2026, 0, 1, 0, 0))).toBe('2026-01-01');
  });

  it('gives the first and last day of the month (AC-21)', () => {
    expect(monthRange(new Date(2026, 9, 15))).toEqual({ dateFrom: '2026-10-01', dateTo: '2026-10-31' });
    expect(monthRange(new Date(2028, 1, 10))).toEqual({ dateFrom: '2028-02-01', dateTo: '2028-02-29' });
  });

  it('gives the previous month, also across a year boundary', () => {
    expect(monthRange(new Date(2026, 9, 15), -1)).toEqual({ dateFrom: '2026-09-01', dateTo: '2026-09-30' });
    expect(monthRange(new Date(2026, 0, 15), -1)).toEqual({ dateFrom: '2025-12-01', dateTo: '2025-12-31' });
  });
});
