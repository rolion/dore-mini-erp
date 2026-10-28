import { Unit } from '../models/unit';
import { Warehouse } from '../models/warehouse';

export function makeUnit(overrides: Partial<Unit> = {}): Unit {
  return { id: 'u-1', name: 'Kilogramo', abbreviation: 'kg', allowsFractions: true, active: true, inUse: false, ...overrides };
}

export function makeWarehouse(overrides: Partial<Warehouse> = {}): Warehouse {
  return { id: 'w-1', name: 'Almacén principal', description: '', active: true, isDefault: true, ...overrides };
}
