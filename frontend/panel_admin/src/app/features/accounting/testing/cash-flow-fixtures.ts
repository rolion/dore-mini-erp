import { CashFlowDto, CashFlowMovementPageDto } from '../models/cash-flow';

export function makeCashFlowDto(overrides: Partial<CashFlowDto> = {}): CashFlowDto {
  return {
    period: { date_from: '2026-05-01', date_to: '2026-05-31' },
    coverage: { cutoff_date: '2026-04-01', partial: false },
    summary: { opening: '0.00', inflow: '2477.00', outflow: '1750.00', net: '727.00', closing: '727.00', transfers: '500.00' },
    accounts: [
      { account_id: 'a-cash', name: 'Caja', opening: '0.00', inflow: '2477.00', outflow: '1750.00', transfers_in: '0.00', transfers_out: '500.00', net: '227.00', closing: '227.00' },
      { account_id: 'a-bank', name: 'Banco', opening: '0.00', inflow: '0.00', outflow: '0.00', transfers_in: '500.00', transfers_out: '0.00', net: '500.00', closing: '500.00' },
    ],
    ...overrides,
  };
}

export function makeMovementPageDto(overrides: Partial<CashFlowMovementPageDto> = {}): CashFlowMovementPageDto {
  return {
    count: 2,
    totals: { inflow: '90.00', outflow: '0.00', transfers_in: '500.00', transfers_out: '500.00' },
    results: [
      { entry_id: 'e-1', accounting_date: '2026-05-10', account: { id: 'a-cash', name: 'Caja' }, description: 'Cobro', origin: { kind: 'PRODUCT', available: true, id: 'o-1', label: 'Venta' }, kind: 'inflow', amount: '90.00', is_reversal: false },
      { entry_id: 'e-2', accounting_date: '2026-05-09', account: { id: 'a-cash', name: 'Caja' }, description: 'Depósito', origin: null, kind: 'transfer_out', amount: '500.00', is_reversal: true },
    ],
    ...overrides,
  };
}
