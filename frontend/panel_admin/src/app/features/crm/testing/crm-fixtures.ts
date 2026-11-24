import { CrmCustomer, CrmCustomerPage } from '../models/crm-customer';

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
