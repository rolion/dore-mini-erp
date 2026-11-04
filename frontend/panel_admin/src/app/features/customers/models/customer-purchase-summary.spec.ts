import { CustomerOrderSummary } from './customer';
import { summarizePurchases, whatsappUrl } from './customer-purchase-summary';

function order(overrides: Partial<CustomerOrderSummary>): CustomerOrderSummary {
  return {
    id: 'o',
    code: 'A-1',
    date: '2026-10-01',
    total: '100.00',
    paidTotal: '100.00',
    balance: '0.00',
    status: 'DELIVERED',
    paymentStatus: 'PAID',
    ...overrides,
  };
}

describe('summarizePurchases', () => {
  it('has no purchases and zero amounts for an empty history (AC-03)', () => {
    expect(summarizePurchases([])).toEqual({
      lastPurchaseDate: null,
      orderCount: 0,
      totalPurchased: '0.00',
      outstandingBalance: '0.00',
      hasOutstandingBalance: false,
    });
  });

  it('adds totals and balances and finds the latest date regardless of the order received (AC-03)', () => {
    const summary = summarizePurchases([
      order({ id: 'a', date: '2026-09-01', total: '0.10', balance: '0.10' }),
      order({ id: 'b', date: '2026-10-30', total: '0.20', balance: '0.00' }),
      order({ id: 'c', date: '2026-10-05', total: '35.00', balance: '5.00' }),
    ]);
    expect(summary).toEqual({
      lastPurchaseDate: '2026-10-30',
      orderCount: 3,
      totalPurchased: '35.30',
      outstandingBalance: '5.10',
      hasOutstandingBalance: true,
    });
  });

  it('ignores cancelled orders in every figure (INV-01)', () => {
    const summary = summarizePurchases([
      order({ id: 'a', date: '2026-09-01', total: '50.00', balance: '10.00' }),
      order({ id: 'b', date: '2026-10-30', total: '999.00', balance: '999.00', status: 'CANCELLED' }),
    ]);
    expect(summary.lastPurchaseDate).toBe('2026-09-01');
    expect(summary.orderCount).toBe(1);
    expect(summary.totalPurchased).toBe('50.00');
    expect(summary.outstandingBalance).toBe('10.00');
  });

  it('treats a history with only cancelled orders as having no purchases (EDGE-02)', () => {
    const summary = summarizePurchases([order({ status: 'CANCELLED' })]);
    expect(summary.lastPurchaseDate).toBeNull();
    expect(summary.orderCount).toBe(0);
    expect(summary.totalPurchased).toBe('0.00');
  });
});

describe('whatsappUrl', () => {
  it('keeps only the digits of the phone (EDGE-03)', () => {
    expect(whatsappUrl('+591 7654-3210')).toBe('https://wa.me/59176543210');
  });

  it('returns null when there are no digits', () => {
    expect(whatsappUrl('')).toBeNull();
    expect(whatsappUrl('n/a')).toBeNull();
  });
});
