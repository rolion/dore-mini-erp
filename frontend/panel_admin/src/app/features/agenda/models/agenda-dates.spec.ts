import { asFullDays, fullDayRange, minutesBetween, repeatUntil, shiftDate } from './agenda-dates';

describe('agenda-dates', () => {
  it('shifts dates across month boundaries', () => {
    expect(shiftDate('2026-11-30', 1)).toBe('2026-12-01');
    expect(shiftDate('2026-11-01', -1)).toBe('2026-10-31');
  });

  it('computes the end of the repetition (AC-08)', () => {
    expect(repeatUntil('week', '2026-11-02')).toBe('2026-11-08');
    expect(repeatUntil('month', '2026-11-02')).toBe('2026-11-30');
    expect(repeatUntil('month', '2026-11-30')).toBe('2026-12-06');
    expect(repeatUntil('month', '2026-12-28')).toBe('2027-01-03');
  });

  it('converts full-day absences in both directions (AC-10)', () => {
    expect(fullDayRange('2026-11-05', '2026-11-06')).toEqual({ starts: '2026-11-05T00:00', ends: '2026-11-07T00:00' });
    expect(asFullDays('2026-11-05T00:00:00-04:00', '2026-11-07T00:00:00-04:00')).toEqual({ from: '2026-11-05', to: '2026-11-06' });
    expect(asFullDays('2026-11-05T07:00:00-04:00', '2026-11-06T07:00:00-04:00')).toBeNull();
    expect(asFullDays('2026-11-05T00:00', '2026-11-05T00:00')).toBeNull();
  });

  it('measures minutes between civil times', () => {
    expect(minutesBetween('2026-11-05T07:00', '2026-11-05T09:30')).toBe(150);
  });
});
