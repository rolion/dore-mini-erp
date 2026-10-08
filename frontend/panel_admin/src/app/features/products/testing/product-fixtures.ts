import { Product } from '../models/product';

export function makeProduct(overrides: Partial<Product> = {}): Product {
  return {
    id: 'p-1',
    name: 'Cuñapé grande',
    description: 'Tradicional',
    salePrice: '35.00',
    active: true,
    createdAt: '2026-10-08T10:00:00Z',
    updatedAt: '2026-10-08T11:00:00Z',
    ...overrides,
  };
}
