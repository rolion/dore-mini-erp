import { ImportCounts, ImportMapping, ImportPreview, ImportRow, ImportRunDetail, ImportUpload } from '../models/sales-import';

export const FULL_MAPPING: ImportMapping = {
  sale_date: 'Fecha',
  product_name: 'Producto',
  quantity: 'Cant',
  unit_price: 'Precio',
  sale_number: null,
  customer_name: null,
  payment_method: null,
  sales_channel: null,
  supplier_name: null,
  unit_cost: null,
  discount: null,
  category: null,
  notes: null,
};

export function makeUpload(overrides: Partial<ImportUpload['capabilities']> = {}, mapping: ImportMapping = FULL_MAPPING): ImportUpload {
  return {
    id: 'run-1',
    filename: 'ventas.csv',
    rowCount: 3,
    headers: ['Fecha', 'Producto', 'Cant', 'Precio'],
    sampleRows: [
      ['01/01/2026', 'Harina', '2', '10.00'],
      ['02/01/2026', 'Azúcar', '1', '5.00'],
    ],
    suggestedMapping: mapping,
    capabilities: {
      customers: true,
      inventory: true,
      purchases: true,
      accounting: true,
      costing: true,
      warehouses: [{ id: 'w-1', name: 'Central', isDefault: true }],
      paymentMethods: ['CASH', 'QR', 'BANK_TRANSFER', 'CARD', 'OTHER'],
      salesChannels: ['WHATSAPP', 'FACEBOOK', 'INSTAGRAM', 'STORE', 'FAIR', 'OTHER'],
      ...overrides,
    },
  };
}

export const PREVIEW: ImportPreview = {
  salesTotal: 3,
  linesTotal: 4,
  toCreate: 2,
  alreadyImported: 1,
  withErrors: 0,
  newProducts: 1,
  existingProducts: 2,
  newCustomers: 0,
  existingCustomers: 0,
  purchasesToCreate: 0,
  unitsToBuy: 0,
  withoutPosting: 0,
  problems: [{ row: 4, saleKey: 'V-3', field: 'quantity', code: 'invalid', message: 'Cantidad inválida' }],
  problemsTotal: 1,
};

export const COUNTS: ImportCounts = { created: 2, skipped: 1, failed: 0, withoutPosting: 0 };

export const ROWS: ImportRow[] = [
  { row: 2, saleKey: 'V-1', status: 'CREATED', code: '', message: 'Cargada', orderId: 'o-1' },
  { row: 3, saleKey: 'V-2', status: 'SKIPPED_DUPLICATE', code: 'dup', message: 'Ya importada', orderId: null },
  { row: 4, saleKey: 'V-3', status: 'FAILED', code: 'x', message: 'Producto inexistente', orderId: null },
  { row: 5, saleKey: 'V-4', status: 'CREATED_WITHOUT_POSTING', code: 'y', message: 'Fecha sin cobertura', orderId: 'o-4' },
];

export const RUN: ImportRunDetail = {
  id: 'run-1',
  filename: 'ventas.csv',
  status: 'COMPLETED',
  createdAt: '2026-11-19T10:00:00Z',
  createdByName: 'ana',
  rowCount: 3,
  counts: COUNTS,
  options: {},
};
