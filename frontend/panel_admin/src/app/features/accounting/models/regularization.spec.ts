import { provideTestTranslations } from '../../../core/i18n/testing';
import { TestBed } from '@angular/core/testing';
import { makeSummaryDto } from '../testing/regularization-fixtures';
import { isRulePartial, reasonLabel, statusAmounts, statusCount, toRequest, toSummary } from './regularization';

describe('regularization model', () => {
  beforeEach(() => TestBed.configureTestingModule({ providers: provideTestTranslations() }));

  it('builds the request from the explicit rules only and skips incomplete rows (AC-15)', () => {
    const request = toRequest({
      dateFrom: '2026-01-01', dateTo: '',
      rules: [
        { method: 'CASH', accountId: 'a-1', from: '', to: '2026-01-31' },
        { method: 'CASH', accountId: 'a-2', from: '2026-02-01', to: '' },
        { method: '', accountId: 'a-3', from: '', to: '' },
        { method: 'QR', accountId: '', from: '', to: '' },
      ],
    });
    expect(request).toEqual({
      date_from: '2026-01-01', date_to: null,
      mapping: { CASH: [{ account_id: 'a-1', to: '2026-01-31' }, { account_id: 'a-2', from: '2026-02-01' }] },
    });
  });

  it('counts and sums per status without mixing currencies', () => {
    const summary = toSummary(makeSummaryDto());
    expect(statusCount(summary, 'missing')).toBe(3);
    expect(statusAmounts(summary, 'missing')).toEqual([{ currency: 'BOB', amount: '175.00' }]);
    expect(statusCount(summary, 'conflict')).toBe(0);
  });

  it('explains each review case with a reason or the differing fields', () => {
    const detail = toSummary(makeSummaryDto()).details[0];
    expect(reasonLabel(detail)).toBe('Método sin regla de mapeo');
    expect(reasonLabel({ ...detail, reason: '', fields: ['amount'] })).toContain('importe');
    expect(reasonLabel({ ...detail, error: 'rechazada' })).toBe('rechazada');
  });

  it('detects half-filled rules but not completely empty rows (REV-04)', () => {
    expect(isRulePartial({ method: 'CASH', accountId: '', from: '', to: '' })).toBeTrue();
    expect(isRulePartial({ method: '', accountId: 'a-1', from: '', to: '' })).toBeTrue();
    expect(isRulePartial({ method: '', accountId: '', from: '2026-01-01', to: '' })).toBeTrue();
    expect(isRulePartial({ method: '', accountId: '', from: '', to: '' })).toBeFalse();
    expect(isRulePartial({ method: 'CASH', accountId: 'a-1', from: '', to: '' })).toBeFalse();
  });
});
