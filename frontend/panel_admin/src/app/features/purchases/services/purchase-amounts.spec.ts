import { isValidPrice, isValidQuantity, lineSubtotal, purchaseTotal } from './purchase-amounts';

describe('purchase-amounts (INV-06, EDGE-01, EDGE-02)', () => {
  it('multiplies quantity by price with two decimals', () => {
    expect(lineSubtotal('2.5', '10.00')).toBe('25.00');
    expect(lineSubtotal('3', '7')).toBe('21.00');
    expect(lineSubtotal('0.5', '3.00')).toBe('1.50');
  });

  it('rounds half up like the server', () => {
    expect(lineSubtotal('0.333', '10.00')).toBe('3.33');
    expect(lineSubtotal('1.005', '1.00')).toBe('1.01');
    expect(lineSubtotal('0.001', '0.01')).toBe('0.00');
  });

  it('accepts a zero price but not a zero quantity', () => {
    expect(lineSubtotal('3', '0')).toBe('0.00');
    expect(lineSubtotal('0', '5')).toBeNull();
  });

  it('returns null while the line is incomplete or invalid', () => {
    for (const [quantity, price] of [['', '1'], ['1', ''], ['abc', '1'], ['1', '-1'], ['1e3', '1'], ['1.0005', '1'], ['1', '1.001']]) {
      expect(lineSubtotal(quantity, price)).withContext(`${quantity} × ${price}`).toBeNull();
    }
  });

  it('does not lose precision with large amounts', () => {
    expect(lineSubtotal('99999999.999', '9999999999.99')).toBe('999999999989000000.00');
    expect(lineSubtotal('12345678.901', '0.07')).toBe('864197.52');
  });

  it('totals only the valid lines', () => {
    expect(purchaseTotal([])).toBe('0.00');
    expect(
      purchaseTotal([
        { quantity: '2', unitPrice: '10.50' },
        { quantity: '0.5', unitPrice: '3.00' },
        { quantity: '', unitPrice: '9' },
      ]),
    ).toBe('22.50');
  });

  it('validates quantities (INV-04)', () => {
    expect(isValidQuantity('1')).toBeTrue();
    expect(isValidQuantity('0.001')).toBeTrue();
    expect(isValidQuantity('0')).toBeFalse();
    expect(isValidQuantity('-1')).toBeFalse();
    expect(isValidQuantity('1.0001')).toBeFalse();
    expect(isValidQuantity('1.5', false)).toBeFalse();
    expect(isValidQuantity('2.000', false)).toBeTrue();
    expect(isValidQuantity('')).toBeFalse();
  });

  it('validates prices (INV-04)', () => {
    expect(isValidPrice('0')).toBeTrue();
    expect(isValidPrice('10.25')).toBeTrue();
    expect(isValidPrice('-0.01')).toBeFalse();
    expect(isValidPrice('1.001')).toBeFalse();
    expect(isValidPrice('')).toBeFalse();
  });
});
