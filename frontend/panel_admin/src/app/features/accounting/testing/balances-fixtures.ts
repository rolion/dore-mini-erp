import { BalanceRowDto, BalancesDto } from '../models/balances';

export function makeBalanceRowDto(overrides: Partial<BalanceRowDto> = {}): BalanceRowDto {
  return {
    account_id: 'a-1', code: '111001', name: 'Caja', account_class: 'ASSET', is_active: true,
    opening_debit_balance: '0.00', opening_credit_balance: '0.00', debit: '1000.00', credit: '300.00',
    debit_balance: '700.00', credit_balance: '0.00', ...overrides,
  };
}

export function makeBalancesDto(overrides: Partial<BalancesDto> = {}): BalancesDto {
  return {
    date_from: null, date_to: null, has_opening: false,
    rows: [
      makeBalanceRowDto(),
      makeBalanceRowDto({ account_id: 'a-2', code: '411001', name: 'Ingresos', account_class: 'INCOME', debit: '300.00',
        credit: '1000.00', debit_balance: '0.00', credit_balance: '700.00' }),
    ],
    totals: { opening_debit_balance: '0.00', opening_credit_balance: '0.00', debit: '1300.00', credit: '1300.00',
      debit_balance: '700.00', credit_balance: '700.00', balanced: true },
    ...overrides,
  };
}
