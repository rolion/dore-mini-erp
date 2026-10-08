import { Customer } from '../models/customer';

export function makeCustomer(overrides: Partial<Customer> = {}): Customer {
  return {
    id: 'c-1',
    name: 'Ana Pérez',
    phone: '+59176543210',
    email: 'ana@example.com',
    notes: 'Cliente frecuente',
    active: true,
    createdAt: '2026-10-08T10:00:00Z',
    updatedAt: '2026-10-08T11:00:00Z',
    ...overrides,
  };
}
