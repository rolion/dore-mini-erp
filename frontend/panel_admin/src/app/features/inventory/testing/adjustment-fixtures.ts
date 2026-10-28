import { StockAdjustment, StockAdjustmentDetail } from '../models/adjustment';

export function makeAdjustment(overrides: Partial<StockAdjustment> = {}): StockAdjustment {
  return {
    id: 'a-1',
    reference: 'AJ-1A2B3C4D',
    createdAt: '2026-10-20T15:30:00Z',
    product: { id: 'p-1', name: 'Arroz' },
    warehouse: { id: 'w-1', name: 'Almacén principal' },
    systemQuantity: '10.0000',
    countedQuantity: '7.0000',
    difference: '-3.0000',
    kind: 'out',
    unitAbbreviation: 'kg',
    user: { id: 'u-1', name: 'ana' },
    status: 'confirmed',
    ...overrides,
  };
}

export function makeAdjustmentDetail(overrides: Partial<StockAdjustmentDetail> = {}): StockAdjustmentDetail {
  return { ...makeAdjustment(), reason: 'Conteo físico', movementId: 'm-9', ...overrides };
}
