import { SummaryDto } from '../models/regularization';

export function makeSummaryDto(overrides: Partial<SummaryDto> = {}): SummaryDto {
  return {
    mode: 'preview',
    total_payments: 4,
    period: { date_from: '2026-03-01', date_to: '2026-03-31' },
    mapping_coverage: [{ method: 'CASH', rules: [{ account_id: 'a-1', account: 'Caja', from: null, to: null }] }],
    unmapped_methods: ['QR', 'CARD'],
    groups: [
      { status: 'missing', origin: 'PRODUCT', account_id: 'a-1', account: 'Caja', currency: 'BOB', count: 2, amount: '125.00' },
      { status: 'missing', origin: 'SERVICE', account_id: 'a-2', account: 'Banco', currency: 'BOB', count: 1, amount: '50.00' },
      { status: 'pending', origin: 'PRODUCT', account_id: null, account: null, currency: 'BOB', count: 1, amount: '30.00' },
    ],
    absent_fields: { author: 2 },
    details: [
      { status: 'pending', outcome: '', origin: 'PRODUCT', payment_id: 'p-6', document_ref: 'o-6', payment_date: '2026-03-10', method: 'CARD', amount: '30.00', currency: 'BOB', reason: 'method_without_mapping', fields: [], error: '' },
    ],
    ...overrides,
  };
}
