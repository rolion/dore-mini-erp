import { amountError, fromCents, toCents } from './payment-amounts';

describe('payment-amounts', () => {
  it('converts texts with up to two decimals to cents (AC-14)', () => {
    expect(toCents('10')).toBe(1000n);
    expect(toCents('10.5')).toBe(1050n);
    expect(toCents(' 0.07 ')).toBe(7n);
    expect(toCents('99999999.99')).toBe(9999999999n);
  });

  it('rejects malformed amounts', () => {
    for (const bad of ['', 'abc', '1.234', '-1', '1,5', '1e3', '.5', '5.']) {
      expect(toCents(bad)).withContext(bad).toBeNull();
    }
  });

  it('formats cents with two decimals', () => {
    expect(fromCents(1050n)).toBe('10.50');
    expect(fromCents(7n)).toBe('0.07');
    expect(fromCents(0n)).toBe('0.00');
  });

  it('validates the amount against the balance (AC-17)', () => {
    expect(amountError('', '50.00')).toContain('obligatorio');
    expect(amountError('abc', '50.00')).toContain('válido');
    expect(amountError('0', '50.00')).toContain('mayor a cero');
    expect(amountError('50.01', '50.00')).toContain('saldo pendiente (Bs 50.00)');
    expect(amountError('50.00', '50.00')).toBeNull();
    expect(amountError('0.01', '50.00')).toBeNull();
  });
});
