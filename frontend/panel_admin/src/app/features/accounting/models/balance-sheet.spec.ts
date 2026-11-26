import { makeBalanceSheetDto } from '../testing/balance-sheet-fixtures';
import { isBalanceSheetEmpty, isBalanceSheetRangeInvalid, isNegativeAmount, isZeroAmount, toBalanceSheet } from './balance-sheet';

describe('balance-sheet model', () => {
  it('maps sections, rows, equity results and totals keeping decimals as text (AC-01, AC-04)', () => {
    const sheet = toBalanceSheet(makeBalanceSheetDto());
    expect(sheet.sections.map((s) => s.key)).toEqual(['ASSET', 'LIABILITY', 'EQUITY']);
    expect(sheet.sections[0].rows[0].closing).toBe('1500.00');
    expect(sheet.sections[0].previousResult).toBeNull();
    expect(sheet.sections[2].periodResult?.closing).toBe('200.00');
    expect(sheet.totals.liabilitiesAndEquity).toBe('1500.00');
    expect(sheet.totals.balanced).toBeTrue();
  });

  it('detects an inverted range, zero and negative amounts', () => {
    expect(isBalanceSheetRangeInvalid({ dateFrom: '2026-05-02', dateTo: '2026-05-01' })).toBeTrue();
    expect(isBalanceSheetRangeInvalid({ dateFrom: '2026-05-01', dateTo: '2026-05-01' })).toBeFalse();
    expect(isZeroAmount('0.00')).toBeTrue();
    expect(isZeroAmount('-0.00')).toBeTrue();
    expect(isZeroAmount('0.01')).toBeFalse();
    expect(isNegativeAmount('-5.00')).toBeTrue();
    expect(isNegativeAmount('-0.00')).toBeFalse();
  });

  it('is empty only when nothing has a balance', () => {
    expect(isBalanceSheetEmpty(toBalanceSheet(makeBalanceSheetDto()))).toBeFalse();
    const zero = { opening: '0.00', movement: '0.00', closing: '0.00' };
    const empty = makeBalanceSheetDto({
      sections: ['ASSET', 'LIABILITY', 'EQUITY'].map((key) => ({ key: key as 'ASSET', rows: [], total: zero })),
      totals: { assets: '0.00', liabilities: '0.00', equity: '0.00', liabilities_and_equity: '0.00', difference: '0.00',
        balanced: true, unclassified_balance: '0.00' },
    });
    expect(isBalanceSheetEmpty(toBalanceSheet(empty))).toBeTrue();
  });
});
