import { StockMovement, StockMovementDetail } from '../models/movement';
import { Unit } from '../models/unit';
import { Warehouse } from '../models/warehouse';

export function makeUnit(overrides: Partial<Unit> = {}): Unit {
  return { id: 'u-1', name: 'Kilogramo', abbreviation: 'kg', allowsFractions: true, active: true, inUse: false, ...overrides };
}

export function makeWarehouse(overrides: Partial<Warehouse> = {}): Warehouse {
  return { id: 'w-1', name: 'Almacén principal', description: '', active: true, isDefault: true, ...overrides };
}

export function makeMovement(overrides: Partial<StockMovement> = {}): StockMovement {
  return {
    id: 'm-1',
    occurredAt: '2026-10-20T15:30:00Z',
    reference: 'PV-1',
    product: { id: 'p-1', name: 'Arroz' },
    warehouse: { id: 'w-1', name: 'Almacén principal' },
    kind: 'out',
    quantityIn: null,
    quantityOut: '2.5000',
    unitAbbreviation: 'kg',
    status: 'confirmed',
    source: { type: 'sales_order', label: 'Pedido de venta', id: '42', line: '', reference: 'PV-1', available: true },
    ...overrides,
  };
}

export function makeMovementDetail(overrides: Partial<StockMovementDetail> = {}): StockMovementDetail {
  return {
    ...makeMovement(),
    quantity: '2.5000',
    reason: 'Venta',
    user: { id: 'u-1', name: 'ana' },
    reversal: { allowed: true, code: null, message: null },
    reversedBy: null,
    reversedById: null,
    reversesId: null,
    createdAt: '2026-10-20T15:30:01Z',
    ...overrides,
  };
}
