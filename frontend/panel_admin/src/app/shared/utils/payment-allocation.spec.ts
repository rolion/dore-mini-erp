import { autoAllocate, halfOf, totalCents } from './payment-allocation';

const LINES = [
  { line_id: 'a', balance: '200.00' },
  { line_id: 'b', balance: '100.00' },
  { line_id: 'c', balance: '0.00' },
];

describe('payment-allocation', () => {
  it('reparte en el orden de las líneas sin superar el saldo de cada una (INV-03)', () => {
    expect(autoAllocate(25000, LINES)).toEqual([{ line_id: 'a', cents: 20000 }, { line_id: 'b', cents: 5000 }]);
    expect(autoAllocate(10000, LINES)).toEqual([{ line_id: 'a', cents: 10000 }]);
    expect(autoAllocate(30000, LINES).reduce((sum, row) => sum + row.cents, 0)).toBe(30000);
  });

  it('no asigna nada con monto cero o negativo y se detiene al agotar el saldo', () => {
    expect(autoAllocate(0, LINES)).toEqual([]);
    expect(autoAllocate(-5, LINES)).toEqual([]);
    expect(autoAllocate(99999, LINES).reduce((sum, row) => sum + row.cents, 0)).toBe(30000);
  });

  it('el 50 % del saldo redondea al centavo hacia arriba (INV-04)', () => {
    expect(halfOf(30000)).toBe(15000);
    expect(halfOf(15001)).toBe(7501);
    expect(halfOf(0)).toBe(0);
  });

  it('suma los saldos de las líneas', () => {
    expect(totalCents(LINES)).toBe(30000);
  });
});
