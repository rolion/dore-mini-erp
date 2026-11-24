import { CrmBoard, CrmStage } from '../models/board';
import { CrmCustomer, CrmCustomerPage } from '../models/crm-customer';

export function makeStage(overrides: Partial<CrmStage> = {}): CrmStage {
  return { id: 's-1', name: 'Nuevo', position: 1, isActive: true, cardCount: 0, ...overrides };
}

export function makeBoard(overrides: Partial<CrmBoard> = {}): CrmBoard {
  return { id: 'b-1', name: 'Ventas', isActive: true, stages: [], ...overrides };
}

export function makeCrmCustomer(overrides: Partial<CrmCustomer> = {}): CrmCustomer {
  return {
    id: 'c-1',
    name: 'Ana Pérez',
    phone: '+59176543210',
    lastPurchaseAt: '2026-11-10',
    orderCount: 2,
    outstandingAmount: '30.00',
    currency: 'BOB',
    ...overrides,
  };
}

export function makeCrmPage(results: CrmCustomer[], count = results.length, meta: Partial<CrmCustomerPage['meta']> = {}): CrmCustomerPage {
  return { count, results, meta: { sales_enabled: true, warehouse_filter_enabled: true, ...meta } };
}
