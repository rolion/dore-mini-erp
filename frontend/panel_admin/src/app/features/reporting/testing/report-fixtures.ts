import {
  ChannelReport,
  CustomersReport,
  DashboardSummary,
  ExpensesReport,
  PendingReport,
  Period,
  ProductsReport,
  SalesReport,
} from '../models/report';

export const MONTH: Period = { kind: 'month', dateFrom: '2026-10-01', dateTo: '2026-10-31' };

export function makeSummary(overrides: Partial<DashboardSummary> = {}): DashboardSummary {
  return {
    period: MONTH,
    salesTotal: '1200.00',
    ordersCount: 4,
    averageTicket: '300.00',
    expensesTotal: '450.00',
    estimatedProfit: '750.00',
    pendingDeliveryCount: 3,
    pendingCollectionCount: 2,
    pendingCollectionBalance: '85.50',
    salesCriteria: 'Ventas: criterio de prueba.',
    ...overrides,
  };
}

export function makeSales(overrides: Partial<SalesReport> = {}): SalesReport {
  return { period: MONTH, total: '1200.00', ordersCount: 4, averageTicket: '300.00', criteria: 'Ventas: criterio.', ...overrides };
}

export function makeExpenses(overrides: Partial<ExpensesReport> = {}): ExpensesReport {
  return {
    period: MONTH,
    total: '170.50',
    categories: [
      { categoryId: 'c1', name: 'Materia prima', active: true, total: '150.50' },
      { categoryId: 'c2', name: 'Empaque', active: false, total: '20.00' },
    ],
    ...overrides,
  };
}

export function makeChannels(overrides: Partial<ChannelReport> = {}): ChannelReport {
  return {
    period: MONTH,
    channels: [
      { salesChannel: 'STORE', ordersCount: 1, total: '100.00' },
      { salesChannel: 'WHATSAPP', ordersCount: 3, total: '300.00' },
    ],
    ...overrides,
  };
}

export function makeProducts(overrides: Partial<ProductsReport> = {}): ProductsReport {
  return {
    period: MONTH,
    limit: 10,
    products: [{ productId: 'p1', productName: 'Pack cuñapé', units: 5, amount: '175.00' }],
    ...overrides,
  };
}

export function makeCustomers(overrides: Partial<CustomersReport> = {}): CustomersReport {
  return {
    period: MONTH,
    limit: 10,
    customers: [{ customerId: 'k1', name: 'Ana Pérez', ordersCount: 2, total: '100.00' }],
    ...overrides,
  };
}

export function makePending(overrides: Partial<PendingReport> = {}): PendingReport {
  return {
    delivery: {
      count: 1,
      rows: [
        {
          id: 'o1',
          orderDate: '2026-10-01',
          customer: { id: 'k1', name: 'Ana Pérez' },
          expectedDeliveryDate: '2026-10-20',
          status: 'IN_PREPARATION',
          paymentStatus: 'PAID',
          total: '70.00',
        },
      ],
    },
    collection: {
      count: 1,
      balanceTotal: '50.00',
      rows: [
        {
          id: 'o2',
          orderDate: '2026-10-02',
          customer: null,
          total: '70.00',
          balance: '50.00',
          status: 'DELIVERED',
          paymentStatus: 'PARTIAL',
        },
      ],
    },
    ...overrides,
  };
}
