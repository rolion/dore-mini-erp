import { provideTestTranslations } from '../../../core/i18n/testing';
import { TestBed } from '@angular/core/testing';
import { TranslateService } from '@ngx-translate/core';
import { makeEntry } from '../testing/entry-fixtures';
import { directionLabel, documentLabel, formatAmount, originLabel, signedAmount, sourceLink, toEntry, toEntryPage } from './entry';
import { makeEntryDto, makeEntryPage } from '../testing/entry-fixtures';

describe('entry model helpers', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [...provideTestTranslations()] });
    TestBed.inject(TranslateService); // arranca el traductor que usa `tr`
  });

  it('formats amounts per currency without converting', () => {
    expect(formatAmount('300.50', 'BOB')).toContain('300.50');
    expect(formatAmount('70.00', 'USD')).toBe('70.00 USD');
  });

  it('links to the order or the commitment only when the source is available (UI-04)', () => {
    expect(sourceLink(makeEntry({ documentRef: 'o-1' }))).toEqual(['/pocketbiz/sales/orders', 'o-1']);
    expect(sourceLink(makeEntry({ origin: 'SERVICE', documentRef: 'quotation/PRO-1' }))).toEqual(['/pocketbiz/receivables', 'quotation', 'PRO-1']);
    expect(sourceLink(makeEntry({ sourceAvailable: false }))).toBeNull();
    expect(sourceLink(makeEntry({ origin: 'SERVICE', documentRef: 'sin-barra' }))).toBeNull();
    expect(sourceLink(makeEntry({ documentRef: '' }))).toBeNull();
  });

  it('signs expenses, labels the new origins and has no link until Expenses and Purchases expose a screen (AC-08)', () => {
    const expense = makeEntry({ origin: 'EXPENSE', direction: 'EXPENSE', amount: '100.00', documentRef: 'gasto-1' });
    expect(signedAmount(expense)).toBe(`−${formatAmount('100.00', 'BOB')}`);
    expect(signedAmount(makeEntry())).toBe(formatAmount('300.50', 'BOB'));
    expect(originLabel('EXPENSE')).toBe('Gastos');
    expect(originLabel('PURCHASE_PAYMENT')).toBe('Pagos de compras');
    expect(directionLabel('EXPENSE')).toBe('Egreso');
    expect(sourceLink(expense)).toBeNull();
    expect(documentLabel(expense)).toBe('gasto-1');
  });

  it('maps direction, classification and reversal links, defaulting old payloads to an income record (AC-07)', () => {
    const reversal = toEntry(makeEntryDto({
      direction: 'INCOME', operation: 'REVERSAL', classification: { id: 'c-1', name: 'Alquiler' }, reversal_of: 'e-0',
    }));
    expect([reversal.operation, reversal.classificationName, reversal.reversalOf, reversal.reversedBy]).toEqual(['REVERSAL', 'Alquiler', 'e-0', null]);
    const legacy = toEntry({ ...makeEntryDto(), direction: undefined, operation: undefined, classification: undefined });
    expect([legacy.direction, legacy.operation, legacy.classificationName]).toEqual(['INCOME', 'RECORD', '']);
    const page = toEntryPage({
      count: 1, results: [], period: { date_from: null, date_to: null },
      coverage: { first_payment_date: null, last_payment_date: null, first_recorded_at: null },
      totals: [{ currency: 'BOB', count: 2, amount: '250.00', by_origin: { PRODUCT: '250.00', SERVICE: '0.00' }, expense: '100.00', by_direction: { net: '150.00' } }],
    });
    expect([page.totals[0].expense, page.totals[0].net]).toEqual(['100.00', '150.00']);
    expect(makeEntryPage().totals[0].net).toBe('300.50');
  });

  it('shows the proforma number for services and a short id for orders', () => {
    expect(documentLabel(makeEntry({ origin: 'SERVICE', documentRef: 'quotation/PRO-1' }))).toBe('PRO-1');
    expect(documentLabel(makeEntry({ documentRef: '7d4b0c1e-aaaa' }))).toBe('7d4b0c1e');
    expect(documentLabel(makeEntry({ documentRef: '' }))).toBe('—');
  });
});
