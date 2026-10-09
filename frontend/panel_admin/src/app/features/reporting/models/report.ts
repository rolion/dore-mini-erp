import type { OrderStatus, PaymentStatus } from '../../sales';
import { SalesChannel } from '../../../shared/models/sales-channel';

export type PeriodKind = 'day' | 'week' | 'month' | 'range';

/** Lo que el usuario pide: un periodo con nombre o un rango. Las fechas efectivas las resuelve el servidor. */
export type PeriodSelection =
  | { kind: 'day' | 'week' | 'month' }
  | { kind: 'range'; dateFrom: string; dateTo: string };

export const DEFAULT_SELECTION: PeriodSelection = { kind: 'month' };

/** Periodo efectivo devuelto por el servidor (fechas `AAAA-MM-DD`, inclusivas). */
export interface Period {
  kind: PeriodKind;
  dateFrom: string;
  dateTo: string;
}

/** Los importes llegan como texto decimal ("1200.00"); el navegador no opera con ellos. */
export interface DashboardSummary {
  period: Period;
  salesTotal: string;
  ordersCount: number;
  /** `null` si no hay pedidos en el periodo. */
  averageTicket: string | null;
  expensesTotal: string;
  estimatedProfit: string;
  pendingDeliveryCount: number;
  pendingCollectionCount: number;
  pendingCollectionBalance: string;
  salesCriteria: string;
}

export interface SalesReport {
  period: Period;
  total: string;
  ordersCount: number;
  averageTicket: string | null;
  criteria: string;
}

export interface CategoryExpense {
  categoryId: string;
  name: string;
  active: boolean;
  total: string;
}

export interface ExpensesReport {
  period: Period;
  total: string;
  categories: CategoryExpense[];
}

export interface ChannelSales {
  salesChannel: SalesChannel;
  ordersCount: number;
  total: string;
}

export interface ChannelReport {
  period: Period;
  channels: ChannelSales[];
}

export interface ProductSales {
  productId: string;
  productName: string;
  units: number;
  /** Suma de subtotales de ítem, antes del descuento del pedido. */
  amount: string;
}

export interface ProductsReport {
  period: Period;
  limit: number;
  products: ProductSales[];
}

export interface CustomerSales {
  customerId: string;
  name: string;
  ordersCount: number;
  total: string;
}

export interface CustomersReport {
  period: Period;
  limit: number;
  customers: CustomerSales[];
}

export interface PendingCustomer {
  id: string;
  name: string;
}

export interface PendingDeliveryRow {
  id: string;
  orderDate: string;
  customer: PendingCustomer | null;
  expectedDeliveryDate: string | null;
  status: OrderStatus;
  paymentStatus: PaymentStatus;
  total: string;
}

export interface PendingCollectionRow {
  id: string;
  orderDate: string;
  customer: PendingCustomer | null;
  total: string;
  balance: string;
  status: OrderStatus;
  paymentStatus: PaymentStatus;
}

export interface PendingReport {
  delivery: { count: number; rows: PendingDeliveryRow[] };
  collection: { count: number; balanceTotal: string; rows: PendingCollectionRow[] };
}

export function isRangeValid(dateFrom: string, dateTo: string): boolean {
  return !!dateFrom && !!dateTo && dateFrom <= dateTo;
}
