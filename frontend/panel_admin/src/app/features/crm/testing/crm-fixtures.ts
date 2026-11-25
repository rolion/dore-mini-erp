import { CrmBoard, CrmStage } from '../models/board';
import { CrmCustomer, CrmCustomerPage } from '../models/crm-customer';
import { CrmLead } from '../models/lead';
import { CrmOpportunity } from '../models/opportunity';

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

export function makeLead(overrides: Partial<CrmLead> = {}): CrmLead {
  return {
    id: 'l-1',
    name: 'Carla Rojas',
    phone: '76543210',
    normalizedPhone: '+59176543210',
    email: 'carla@ejemplo.com',
    convertedCustomerId: null,
    createdAt: '2026-11-20T10:00:00Z',
    ...overrides,
  };
}

export function makeOpportunity(overrides: Partial<CrmOpportunity> = {}): CrmOpportunity {
  return {
    id: 'o-1',
    boardId: 'b-1',
    stageId: 's-1',
    lead: { id: 'l-1', name: 'Carla Rojas', phone: '+59176543210' },
    customer: null,
    title: 'Combo familiar',
    owner: { id: 7, name: 'Ana Admin' },
    amount: '150.00',
    currency: 'BOB',
    nextActionAt: null,
    status: 'open',
    closedAt: null,
    orderId: null,
    lostReason: '',
    createdAt: '2026-11-20T10:00:00Z',
    ...overrides,
  };
}
