import { BalanceSheetDto, SheetRowDto } from '../models/balance-sheet';

const ZERO = { opening: '0.00', movement: '0.00', closing: '0.00' };

export function makeSheetRowDto(overrides: Partial<SheetRowDto> = {}): SheetRowDto {
  return {
    account_id: 'a-1', code: '111001', name: 'Caja', is_active: true,
    opening: '0.00', movement: '1500.00', closing: '1500.00', ...overrides,
  };
}

export function makeBalanceSheetDto(overrides: Partial<BalanceSheetDto> = {}): BalanceSheetDto {
  return {
    date_from: null, date_to: null, has_opening: false,
    sections: [
      { key: 'ASSET', rows: [makeSheetRowDto()], total: { opening: '0.00', movement: '1500.00', closing: '1500.00' } },
      { key: 'LIABILITY', rows: [makeSheetRowDto({ account_id: 'a-2', code: '211001', name: 'Préstamo', movement: '500.00',
        closing: '500.00' })], total: { opening: '0.00', movement: '500.00', closing: '500.00' } },
      { key: 'EQUITY', rows: [makeSheetRowDto({ account_id: 'a-3', code: '311001', name: 'Capital', movement: '800.00',
        closing: '800.00' })], total: { opening: '0.00', movement: '1000.00', closing: '1000.00' },
        previous_result: { ...ZERO }, period_result: { opening: '0.00', movement: '200.00', closing: '200.00' } },
    ],
    totals: { assets: '1500.00', liabilities: '500.00', equity: '1000.00', liabilities_and_equity: '1500.00',
      difference: '0.00', balanced: true, unclassified_balance: '0.00' },
    ...overrides,
  };
}
