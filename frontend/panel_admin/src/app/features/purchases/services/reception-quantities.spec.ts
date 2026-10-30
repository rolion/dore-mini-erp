import { isPositive, isReceivable, pendingAfter, positiveQuantity, quantityError } from './reception-quantities';

describe('reception quantities (AC-20)', () => {
  it('omits empty and zero lines without an error', () => {
    for (const text of ['', '  ', '0', '0.000']) {
      expect(quantityError(text, '5.000', true)).withContext(text).toBeNull();
      expect(isReceivable(text)).withContext(text).toBeFalse();
    }
  });

  it('rejects negative, non numeric and too precise values', () => {
    expect(quantityError('-1', '5.000', true)).toContain('negativa');
    expect(quantityError('abc', '5.000', true)).toContain('número válido');
    expect(quantityError('1,5', '5.000', true)).toContain('número válido');
    expect(quantityError('1.0001', '5.000', true)).toContain('3 decimales');
  });

  it('does not allow fractions in whole units', () => {
    expect(quantityError('1.5', '5.000', false)).toContain('no admite fracciones');
    expect(quantityError('2', '5.000', false)).toBeNull();
    expect(quantityError('1.5', '5.000', true)).toBeNull();
  });

  it('never exceeds the pending quantity', () => {
    expect(quantityError('5', '5.000', true)).toBeNull();
    expect(quantityError('5.001', '5.000', true)).toContain('pendiente (5.000)');
    expect(quantityError('1', '0.000', true)).toContain('pendiente');
  });

  it('computes what is left and normalizes to 3 decimals', () => {
    expect(positiveQuantity('2.5')).toBe('2.500');
    expect(positiveQuantity('0')).toBeNull();
    expect(pendingAfter('10.000', '4')).toBe('6.000');
    expect(pendingAfter('1.000', '4')).toBe('0.000');
    expect(isPositive('0.001')).toBeTrue();
    expect(isPositive('0.000')).toBeFalse();
  });
});
