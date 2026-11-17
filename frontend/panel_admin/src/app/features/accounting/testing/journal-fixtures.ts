import { JournalDetailDto, JournalEntryDetail, JournalRow, JournalRowDto, toJournalDetail, toJournalRow } from '../models/journal';

export function makeJournalRowDto(overrides: Partial<JournalRowDto> = {}): JournalRowDto {
  return {
    id: 'j-1', accounting_date: '2026-05-10', description: 'Servicio', source: 'MANUAL', origin: null, currency: 'BOB',
    total: '500.00', created_by_name: 'Ana', created_at: '2026-05-10T12:00:00Z', is_reversal: false, reversed_by_id: null,
    ...overrides,
  };
}

export function makeJournalRow(overrides: Partial<JournalRowDto> = {}): JournalRow {
  return toJournalRow(makeJournalRowDto(overrides));
}

export function makeJournalDetailDto(overrides: Partial<JournalDetailDto> = {}): JournalDetailDto {
  return {
    ...makeJournalRowDto(),
    period: { id: 'p-1', name: 'Q2' },
    lines: [
      { position: 0, account: { id: 'a-1', code: '111001', name: 'Caja' }, debit: '200.00', credit: '0.00', memo: '' },
      { position: 1, account: { id: 'a-2', code: '111002', name: 'Banco' }, debit: '300.00', credit: '0.00', memo: '' },
      { position: 2, account: { id: 'a-3', code: '411001', name: 'Ingresos servicios' }, debit: '0.00', credit: '500.00', memo: '' },
    ],
    total_debit: '500.00', total_credit: '500.00', reverses_id: null, reversal_reason: '', can_reverse: true,
    ...overrides,
  };
}

export function makeJournalDetail(overrides: Partial<JournalDetailDto> = {}): JournalEntryDetail {
  return toJournalDetail(makeJournalDetailDto(overrides));
}
