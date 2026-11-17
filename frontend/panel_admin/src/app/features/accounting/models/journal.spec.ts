import { provideTestTranslations } from '../../../core/i18n/testing';
import { TestBed } from '@angular/core/testing';
import {
  DraftLine,
  JournalDraft,
  draftBlockers,
  draftTotals,
  formatCents,
  journalOriginLink,
  parseCents,
  toJournalBody,
  toJournalError,
} from './journal';

const line = (accountId: string, debit = '', credit = ''): DraftLine => ({ accountId, debit, credit });
const draft = (lines: DraftLine[], overrides: Partial<JournalDraft> = {}): JournalDraft => ({
  accountingDate: '2026-05-10', description: 'Servicio', lines, ...overrides,
});
const sale = (): DraftLine[] => [line('cash', '200'), line('bank', '300'), line('income', '', '500')];

describe('journal model', () => {
  beforeEach(() => TestBed.configureTestingModule({ providers: [...provideTestTranslations()] }));

  it('parses amounts in exact cents, never floats (AC-08)', () => {
    expect([parseCents('200'), parseCents('200.5'), parseCents('0,10'), parseCents(''), parseCents('0.1')]).toEqual([20000, 20050, 10, 0, 10]);
    expect([parseCents('1.234'), parseCents('-1'), parseCents('abc'), parseCents('1e3')]).toEqual([null, null, null, null]);
    expect(formatCents(30)).toBe('0.30');
    expect(formatCents(20050)).toBe('200.50');
  });

  it('totals the service sale 500 with difference 0 and allows confirming (AC-01, AC-08)', () => {
    const totals = draftTotals(sale());
    expect([totals.debit, totals.credit, totals.difference]).toEqual([50000, 50000, 0]);
    expect(draftBlockers(draft(sale()))).toEqual([]);
  });

  it('blocks confirming with a difference of 1 (AC-02)', () => {
    const lines = [line('cash', '200'), line('bank', '300'), line('income', '', '499')];
    expect(draftTotals(lines).difference).toBe(100);
    expect(draftBlockers(draft(lines)).length).toBeGreaterThan(0);
  });

  it('blocks missing date or description, fewer than two lines or accounts, both sides and zero totals', () => {
    expect(draftBlockers(draft(sale(), { accountingDate: '' })).length).toBe(1);
    expect(draftBlockers(draft(sale(), { description: '  ' })).length).toBe(1);
    expect(draftBlockers(draft([line('cash', '5')])).length).toBeGreaterThan(0);
    expect(draftBlockers(draft([line('cash', '5'), line('cash', '', '5')])).length).toBeGreaterThan(0);
    expect(draftBlockers(draft([line('cash', '5', '5'), line('bank', '', '5')])).length).toBeGreaterThan(0);
    expect(draftBlockers(draft([line('', '5'), line('bank', '', '5')])).length).toBeGreaterThan(0);
    expect(draftBlockers(draft([line('cash'), line('bank')])).length).toBeGreaterThan(0);
  });

  it('builds the API body with one side per line and normalized decimals', () => {
    expect(toJournalBody(draft(sale(), { description: ' Servicio ' }))).toEqual({
      accounting_date: '2026-05-10', description: 'Servicio',
      lines: [{ account_id: 'cash', debit: '200.00' }, { account_id: 'bank', debit: '300.00' }, { account_id: 'income', credit: '500.00' }],
    });
  });

  it('maps API errors keeping the server messages by field', () => {
    const error = toJournalError(400, { lines: ['No cuadra'], accounting_date: ['Cerrado'] });
    expect(error.status).toBe(400);
    expect(error.fieldErrors['lines']).toEqual(['No cuadra']);
    expect(toJournalError(404, {}).status).toBe(404);
    expect(toJournalError(0, null).status).toBe(0);
    expect(toJournalError(500, {}).message).not.toBe('');
  });

  it('links an origin only when the module is enabled and the document has a screen (AC-05)', () => {
    expect(journalOriginLink(null)).toBeNull();
    expect(journalOriginLink({ kind: 'PRODUCT', id: 'o-1', available: false })).toBeNull();
    expect(journalOriginLink({ kind: 'PRODUCT', id: 'o-1', available: true })).toEqual(['/pocketbiz/sales/orders', 'o-1']);
    expect(journalOriginLink({ kind: 'EXPENSE', id: 'x', available: true })).toBeNull();
  });
});
