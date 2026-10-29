import { Supplier } from '../models/supplier';

export function makeSupplier(overrides: Partial<Supplier> = {}): Supplier {
  return {
    id: 's-1',
    name: 'Distribuidora Sur',
    taxId: 'NIT-1020',
    phone: '76543210',
    email: 'ventas@sur.com',
    notes: 'Entrega los martes',
    active: true,
    createdAt: '2026-10-29T10:00:00Z',
    updatedAt: '2026-10-29T11:00:00Z',
    ...overrides,
  };
}
