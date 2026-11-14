import { Entry, EntryDto, EntryPage } from '../models/entry';

export function makeEntryDto(overrides: Partial<EntryDto> = {}): EntryDto {
  return {
    id: 'e-1',
    account: { id: 'a-1', name: 'Caja', currency: 'BOB' },
    currency: 'BOB',
    amount: '300.50',
    payment_date: '2026-11-01',
    created_at: '2026-11-02T10:00:00Z',
    method: 'CASH',
    method_label: 'Efectivo',
    recorded_by_name: 'Ana',
    origin: { kind: 'PRODUCT', label: 'Productos' },
    source: { document_ref: '7d4b0c1e-aaaa', receipt_number: '', available: true },
    ...overrides,
  };
}

export function makeEntry(overrides: Partial<Entry> = {}): Entry {
  return {
    id: 'e-1', accountId: 'a-1', accountName: 'Caja', currency: 'BOB', amount: '300.50', paymentDate: '2026-11-01',
    createdAt: '2026-11-02T10:00:00Z', method: 'CASH', methodLabel: 'Efectivo', recordedByName: 'Ana', origin: 'PRODUCT',
    sourceId: 'p-1', documentRef: '7d4b0c1e-aaaa', receiptNumber: '', sourceAvailable: true, ...overrides,
  };
}

export function makeEntryPage(results: Entry[] = [makeEntry()], overrides: Partial<EntryPage> = {}): EntryPage {
  return {
    count: results.length,
    results,
    totals: results.length
      ? [{ currency: 'BOB', count: results.length, amount: '300.50', byOrigin: { PRODUCT: '300.50', SERVICE: '0.00' } }]
      : [],
    coverage: { firstPaymentDate: '2026-10-05', lastPaymentDate: '2026-11-01', firstRecordedAt: '2026-11-02T10:00:00Z' },
    ...overrides,
  };
}
