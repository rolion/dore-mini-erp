import { Receipt, ReceiptSummary, ReceptionForm, ReceptionFormLine } from '../models/receipt';

export function makeFormLine(overrides: Partial<ReceptionFormLine> = {}): ReceptionFormLine {
  return {
    itemId: 'i-1',
    productId: 'p-1',
    productName: 'Harina',
    unitAbbreviation: 'kg',
    allowsFractions: true,
    tracksStock: false,
    ordered: '10.000',
    received: '4.000',
    pending: '6.000',
    ...overrides,
  };
}

export function makeReceptionForm(overrides: Partial<ReceptionForm> = {}): ReceptionForm {
  return {
    inventoryEnabled: false,
    warehouses: [],
    warehouseId: null,
    lines: [makeFormLine(), makeFormLine({ itemId: 'i-2', productId: 'p-2', productName: 'Cajas', unitAbbreviation: 'u', allowsFractions: false, ordered: '4.000', received: '0.000', pending: '4.000' })],
    ...overrides,
  };
}

export function makeReceiptSummary(overrides: Partial<ReceiptSummary> = {}): ReceiptSummary {
  return {
    id: 'r-1',
    reference: 'REC-1A2B3C4D',
    receiptDate: '2026-10-30',
    status: 'confirmed',
    userName: 'ana',
    linesCount: 1,
    ...overrides,
  };
}

export function makeReceipt(overrides: Partial<Receipt> = {}): Receipt {
  return {
    id: 'r-1',
    reference: 'REC-1A2B3C4D',
    purchase: { id: 'c-1', reference: 'COM-1A2B3C4D' },
    receiptDate: '2026-10-30',
    status: 'confirmed',
    userName: 'ana',
    createdAt: '2026-10-30T12:00:00Z',
    warehouse: null,
    lines: [{ itemId: 'i-1', productId: 'p-1', productName: 'Harina', unitAbbreviation: 'kg', quantity: '4.000', stockEntry: null }],
    inventoryMode: null,
    inventoryAvailable: false,
    movements: null,
    ...overrides,
  };
}
