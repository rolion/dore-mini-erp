import { Payment } from '../models/payment';

export function makePayment(overrides: Partial<Payment> = {}): Payment {
  return {
    id: 'pay-1',
    reference: 'PAG-1A2B3C4D',
    amount: '10.00',
    paymentMethod: 'CASH',
    paymentDate: '2026-10-30',
    status: 'confirmed',
    userName: 'ana',
    createdAt: '2026-10-30T12:00:00Z',
    ...overrides,
  };
}
