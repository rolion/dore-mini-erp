import { fromCents, localToday, toCents } from './receivable';

describe('importes en centavos', () => {
  it('parsea importes con hasta dos decimales y rechaza el resto', () => {
    expect(toCents('100')).toBe(10000);
    expect(toCents('100.5')).toBe(10050);
    expect(toCents('0,05')).toBe(5);
    for (const bad of ['', 'abc', '-1', '1.005', '1.2.3', null, undefined]) expect(toCents(bad)).toBeNull();
  });

  it('formatea sin errores de coma flotante', () => {
    expect(fromCents(toCents('0.10')! + toCents('0.20')!)).toBe('0.30');
    expect(fromCents(15000)).toBe('150.00');
  });
});

describe('localToday', () => {
  it('usa el día local y no el UTC', () => {
    // 5 nov 2026 23:30 en hora local: toISOString podría dar el día 6 en zonas al oeste de UTC.
    expect(localToday(new Date(2026, 10, 5, 23, 30))).toBe('2026-11-05');
    expect(localToday(new Date(2026, 0, 2, 0, 5))).toBe('2026-01-02');
  });
});
