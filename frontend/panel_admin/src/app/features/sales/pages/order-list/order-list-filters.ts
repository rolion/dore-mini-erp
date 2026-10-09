import { ParamMap, Params } from '@angular/router';
import {
  ORDER_STATUSES,
  OrderDateField,
  OrderListParams,
  OrderStatus,
  OrderCustomer,
  PAYMENT_STATUSES,
  PaymentStatus,
  SALES_CHANNELS,
  SalesChannel,
} from '../../models/order';

/** Valores del filtro "Estado de entrega": un estado, o dos agrupaciones usadas por los atajos. */
export type StatusKey = 'ALL' | 'PENDING_DELIVERY' | 'NOT_CANCELLED' | OrderStatus;
/** Valores del filtro "Estado de pago": un estado, o "con saldo pendiente" (`has_balance`). */
export type PaymentKey = 'ALL' | 'WITH_BALANCE' | PaymentStatus;

export interface ListFilters {
  statusKey: StatusKey;
  paymentKey: PaymentKey;
  channel: SalesChannel | '';
  customer: OrderCustomer | null;
  dateField: OrderDateField;
  dateFrom: string;
  dateTo: string;
}

export interface ListState extends ListFilters {
  /** Página base 1. */
  page: number;
}

export const DEFAULT_FILTERS: ListFilters = {
  statusKey: 'ALL',
  paymentKey: 'ALL',
  channel: '',
  customer: null,
  dateField: 'order_date',
  dateFrom: '',
  dateTo: '',
};

export const PENDING_DELIVERY_STATUSES: readonly OrderStatus[] = ['NEW', 'IN_PREPARATION', 'READY'];
export const NOT_CANCELLED_STATUSES: readonly OrderStatus[] = ['NEW', 'IN_PREPARATION', 'READY', 'DELIVERED'];

export interface Shortcut {
  id: 'all' | 'pending' | 'receivable' | 'delivered' | 'cancelled';
  label: string;
  statusKey: StatusKey;
  paymentKey: PaymentKey;
}

/** Los atajos solo fijan los filtros finos: el usuario ve qué se aplicó y puede ajustarlo. */
export const SHORTCUTS: readonly Shortcut[] = [
  { id: 'all', label: 'Todos', statusKey: 'ALL', paymentKey: 'ALL' },
  { id: 'pending', label: 'Pendientes de entrega', statusKey: 'PENDING_DELIVERY', paymentKey: 'ALL' },
  { id: 'receivable', label: 'Por cobrar', statusKey: 'NOT_CANCELLED', paymentKey: 'WITH_BALANCE' },
  { id: 'delivered', label: 'Entregados', statusKey: 'DELIVERED', paymentKey: 'ALL' },
  { id: 'cancelled', label: 'Cancelados', statusKey: 'CANCELLED', paymentKey: 'ALL' },
];

export function statusesFor(key: StatusKey): OrderStatus[] | undefined {
  switch (key) {
    case 'ALL':
      return undefined;
    case 'PENDING_DELIVERY':
      return [...PENDING_DELIVERY_STATUSES];
    case 'NOT_CANCELLED':
      return [...NOT_CANCELLED_STATUSES];
    default:
      return [key];
  }
}

export function toListParams(state: ListState, pageSize: number): OrderListParams {
  const params: OrderListParams = { page: state.page, pageSize };
  const status = statusesFor(state.statusKey);
  if (status) params.status = status;
  if (state.paymentKey === 'WITH_BALANCE') {
    params.hasBalance = true;
  } else if (state.paymentKey !== 'ALL') {
    params.paymentStatus = [state.paymentKey];
  }
  if (state.channel) params.salesChannel = state.channel;
  if (state.customer) params.customerId = state.customer.id;
  if (state.dateFrom || state.dateTo) {
    params.dateField = state.dateField;
    if (state.dateFrom) params.dateFrom = state.dateFrom;
    if (state.dateTo) params.dateTo = state.dateTo;
  }
  // Pendientes de entrega: las más próximas primero; el resto, por fecha de pedido (más recientes primero).
  params.ordering = state.statusKey === 'PENDING_DELIVERY' ? 'expected_delivery_date' : '-order_date';
  return params;
}

export function hasActiveFilters(filters: ListFilters): boolean {
  return (
    filters.statusKey !== DEFAULT_FILTERS.statusKey ||
    filters.paymentKey !== DEFAULT_FILTERS.paymentKey ||
    !!filters.channel ||
    !!filters.customer ||
    !!filters.dateFrom ||
    !!filters.dateTo
  );
}

export function activeShortcut(filters: ListFilters): Shortcut['id'] | null {
  return SHORTCUTS.find((s) => s.statusKey === filters.statusKey && s.paymentKey === filters.paymentKey)?.id ?? null;
}

const STATUS_KEYS: readonly string[] = ['PENDING_DELIVERY', 'NOT_CANCELLED', ...ORDER_STATUSES];
const PAYMENT_KEYS: readonly string[] = ['WITH_BALANCE', ...PAYMENT_STATUSES];

function oneOf<T extends string>(value: string | null, allowed: readonly string[], fallback: T): T {
  return value !== null && allowed.includes(value) ? (value as T) : fallback;
}

/** URL → estado. Los valores desconocidos caen al valor por defecto (una URL vieja nunca rompe la pantalla). */
export function parseState(params: ParamMap): ListState {
  const customerId = params.get('customer');
  const page = Number(params.get('page'));
  return {
    statusKey: oneOf<StatusKey>(params.get('status'), STATUS_KEYS, 'ALL'),
    paymentKey: oneOf<PaymentKey>(params.get('pay'), PAYMENT_KEYS, 'ALL'),
    channel: oneOf<SalesChannel | ''>(params.get('channel'), SALES_CHANNELS, ''),
    customer: customerId ? { id: customerId, name: params.get('customer_name') ?? '' } : null,
    dateField: oneOf<OrderDateField>(params.get('date_field'), ['order_date', 'expected_delivery_date'], 'order_date'),
    dateFrom: params.get('from') ?? '',
    dateTo: params.get('to') ?? '',
    page: Number.isInteger(page) && page >= 1 ? page : 1,
  };
}

/** Estado → query params; lo que está por defecto no se escribe en la URL. */
export function serializeState(state: ListState): Params {
  return {
    status: state.statusKey !== 'ALL' ? state.statusKey : null,
    pay: state.paymentKey !== 'ALL' ? state.paymentKey : null,
    channel: state.channel || null,
    customer: state.customer?.id ?? null,
    customer_name: state.customer?.name ?? null,
    date_field: state.dateField !== 'order_date' ? state.dateField : null,
    from: state.dateFrom || null,
    to: state.dateTo || null,
    page: state.page > 1 ? String(state.page) : null,
  };
}
