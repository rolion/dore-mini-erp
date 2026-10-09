import { MoneyPipe } from './money.pipe';

describe('MoneyPipe', () => {
  const pipe = new MoneyPipe();

  it('prefixes the amount without touching its digits (UI-05)', () => {
    expect(pipe.transform('70.00')).toBe('Bs 70.00');
    expect(pipe.transform('0.10')).toBe('Bs 0.10');
    expect(pipe.transform('9999999999.99')).toBe('Bs 9999999999.99');
  });

  it('shows a dash when there is no amount', () => {
    expect(pipe.transform(null)).toBe('—');
    expect(pipe.transform(undefined)).toBe('—');
    expect(pipe.transform('')).toBe('—');
  });
});
