import { sumMoney } from './decimal-sum';

describe('sumMoney', () => {
  it('adds decimals exactly, without floating point drift (INV-01)', () => {
    expect(sumMoney(['0.10', '0.20'])).toBe('0.30');
    expect(sumMoney(['120.50', '35.00', '0.05'])).toBe('155.55');
  });

  it('returns 0.00 for no values', () => {
    expect(sumMoney([])).toBe('0.00');
  });

  it('ignores empty or invalid values', () => {
    expect(sumMoney(['', 'abc', '10.00'])).toBe('10.00');
  });

  it('handles integers, large amounts and carries across the decimal point', () => {
    expect(sumMoney(['5', '0.99', '0.01'])).toBe('6.00');
    expect(sumMoney(['99999999999999.99', '0.01'])).toBe('100000000000000.00');
  });

  it('handles negative values and more than two decimals', () => {
    expect(sumMoney(['10.00', '-12.50'])).toBe('-2.50');
    expect(sumMoney(['0.125', '0.125'])).toBe('0.250');
  });
});
