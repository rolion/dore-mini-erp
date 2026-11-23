import {
  discountProblem,
  formatCents,
  lineSubtotal,
  maxDiscountAmount,
  subtotalCents,
  toCents,
  totalCents,
} from './order-amounts';

describe('order-amounts', () => {
  it('parses decimals with up to 2 places and rejects the rest', () => {
    expect(toCents('35')).toBe(3500n);
    expect(toCents('35.5')).toBe(3550n);
    expect(toCents('0.05')).toBe(5n);
    for (const bad of ['', 'abc', '1.234', '-1', '1,5']) expect(toCents(bad)).toBeNull();
  });

  it('formats cents with two decimals', () => {
    expect(formatCents(7000n)).toBe('70.00');
    expect(formatCents(5n)).toBe('0.05');
  });

  it('computes a line subtotal as price × whole quantity (AC-02)', () => {
    expect(lineSubtotal('35.00', 2)).toBe('70.00');
    expect(lineSubtotal('0.10', 3)).toBe('0.30'); // sin errores de coma flotante
    expect(lineSubtotal('35.00', 0)).toBeNull();
    expect(lineSubtotal('x', 1)).toBeNull();
  });

  it('adds the valid lines and subtracts the discount (AC-03)', () => {
    const subtotal = subtotalCents([
      { unitPrice: '35.00', quantity: 2 },
      { unitPrice: '10.50', quantity: 1 },
    ]);
    expect(formatCents(subtotal)).toBe('80.50');
    expect(formatCents(totalCents(subtotal, '5.25'))).toBe('75.25');
    expect(formatCents(totalCents(subtotal, ''))).toBe('80.50');
    expect(formatCents(totalCents(subtotal, 'zz'))).toBe('80.50');
  });

  it('limits the discount to the subtotal and to the configured percentage (AC-04)', () => {
    const subtotal = 10000n; // 100.00
    expect(maxDiscountAmount(subtotal, '10')).toBe('10.00');
    expect(maxDiscountAmount(subtotal, '12.5')).toBe('12.50');
    expect(discountProblem('', subtotal, '10')).toBeNull();
    expect(discountProblem('10.00', subtotal, '10')).toBeNull();
    expect(discountProblem('10.01', subtotal, '10')).toBe('above_percent');
    expect(discountProblem('100.01', subtotal, '100')).toBe('above_subtotal');
    expect(discountProblem('1.234', subtotal, '100')).toBe('invalid');
    expect(discountProblem('0', 0n, '10')).toBeNull();
  });
});
