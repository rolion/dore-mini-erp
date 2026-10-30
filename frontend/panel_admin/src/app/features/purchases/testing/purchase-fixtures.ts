import { Purchase, PurchaseItem, PurchaseSummary } from '../models/purchase';

export function makePurchaseItem(overrides: Partial<PurchaseItem> = {}): PurchaseItem {
  return {
    id: 'i-1',
    productId: 'p-1',
    productName: 'Harina',
    unitAbbreviation: 'kg',
    quantity: '2.500',
    unitPrice: '10.00',
    subtotal: '25.00',
    receivedQuantity: '0.000',
    pendingQuantity: '2.500',
    ...overrides,
  };
}

export function makePurchase(overrides: Partial<Purchase> = {}): Purchase {
  return {
    id: 'c-1',
    supplier: { id: 's-1', name: 'Distribuidora Sur', active: true },
    purchaseDate: '2026-10-29',
    externalReference: 'F-100',
    notes: 'Entrega el martes',
    status: 'draft',
    currency: 'BOB',
    editable: true,
    reference: 'COM-1A2B3C4D',
    receptionStatus: 'not_received',
    paymentStatus: 'unpaid',
    confirmedAt: null,
    cancelledAt: null,
    cancellationReason: '',
    allowedActions: ['edit', 'confirm', 'cancel'],
    items: [makePurchaseItem()],
    total: '25.00',
    paidTotal: '0.00',
    balance: '25.00',
    createdAt: '2026-10-29T10:00:00Z',
    updatedAt: '2026-10-29T11:00:00Z',
    ...overrides,
  };
}

export function makePurchaseSummary(overrides: Partial<PurchaseSummary> = {}): PurchaseSummary {
  return {
    id: 'c-1',
    purchaseDate: '2026-10-29',
    supplier: { id: 's-1', name: 'Distribuidora Sur' },
    externalReference: 'F-100',
    total: '25.00',
    currency: 'BOB',
    status: 'draft',
    itemsCount: 1,
    ...overrides,
  };
}

export function makeConfirmedPurchase(overrides: Partial<Purchase> = {}): Purchase {
  return makePurchase({
    status: 'confirmed',
    editable: false,
    confirmedAt: '2026-10-30T12:00:00Z',
    allowedActions: ['receive', 'pay', 'cancel'],
    ...overrides,
  });
}

export function makeCancelledPurchase(overrides: Partial<Purchase> = {}): Purchase {
  return makePurchase({
    status: 'cancelled',
    editable: false,
    cancelledAt: '2026-10-31T09:30:00Z',
    cancellationReason: 'Pedido duplicado',
    allowedActions: [],
    ...overrides,
  });
}
