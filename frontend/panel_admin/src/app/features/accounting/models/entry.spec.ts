import { provideTestTranslations } from '../../../core/i18n/testing';
import { TestBed } from '@angular/core/testing';
import { TranslateService } from '@ngx-translate/core';
import { makeEntry } from '../testing/entry-fixtures';
import { documentLabel, formatAmount, sourceLink } from './entry';

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

  it('shows the proforma number for services and a short id for orders', () => {
    expect(documentLabel(makeEntry({ origin: 'SERVICE', documentRef: 'quotation/PRO-1' }))).toBe('PRO-1');
    expect(documentLabel(makeEntry({ documentRef: '7d4b0c1e-aaaa' }))).toBe('7d4b0c1e');
    expect(documentLabel(makeEntry({ documentRef: '' }))).toBe('—');
  });
});
