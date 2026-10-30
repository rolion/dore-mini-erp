import { ParamMap, Params } from '@angular/router';
import {
  PAYMENT_STATUS_LABELS,
  PURCHASE_STATUS_LABELS,
  PaymentFilter,
  PaymentStatus,
  PurchaseListParams,
  PurchaseStatus,
  RECEPTION_STATUS_LABELS,
  ReceptionStatus,
} from '../../models/purchase';

/** Valores de los filtros de la lista; el texto vacío significa «sin filtrar». */
export interface PurchaseListFilters {
  supplierId: string;
  dateFrom: string;
  dateTo: string;
  status: PurchaseStatus | '';
  receptionStatus: ReceptionStatus | '';
  paymentStatus: PaymentFilter | '';
  search: string;
}

export const EMPTY_FILTERS: PurchaseListFilters = {
  supplierId: '',
  dateFrom: '',
  dateTo: '',
  status: '',
  receptionStatus: '',
  paymentStatus: '',
  search: '',
};

export interface FilterOption<T extends string> {
  value: T | '';
  label: string;
}

const optionsFrom = <T extends string>(allLabel: string, labels: Readonly<Record<T, string>>): FilterOption<T>[] => [
  { value: '', label: allLabel },
  ...(Object.keys(labels) as T[]).map((value) => ({ value, label: labels[value] })),
];

export const STATUS_OPTIONS = optionsFrom<PurchaseStatus>('Todos', PURCHASE_STATUS_LABELS);
export const RECEPTION_OPTIONS = optionsFrom<ReceptionStatus>('Todas', RECEPTION_STATUS_LABELS);
export const PAYMENT_OPTIONS: FilterOption<PaymentFilter>[] = [
  { value: '', label: 'Todos' },
  { value: 'pending', label: 'Pago pendiente' },
  ...(Object.keys(PAYMENT_STATUS_LABELS) as PaymentStatus[]).map((value) => ({
    value,
    label: PAYMENT_STATUS_LABELS[value],
  })),
];

/** Devuelve `value` si es una de las opciones; un valor desconocido de la URL se ignora. */
function oneOf<T extends string>(value: string | null, options: FilterOption<T>[]): T | '' {
  return options.some((o) => o.value !== '' && o.value === value) ? (value as T) : '';
}

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;
const isoDate = (value: string | null): string => (value && ISO_DATE.test(value) ? value : '');

/** Lee los filtros de la URL (`supplierId` se conserva con ese nombre por compatibilidad). */
export function filtersFromParams(params: ParamMap): PurchaseListFilters {
  return {
    supplierId: params.get('supplierId') ?? '',
    dateFrom: isoDate(params.get('dateFrom')),
    dateTo: isoDate(params.get('dateTo')),
    status: oneOf(params.get('status'), STATUS_OPTIONS),
    receptionStatus: oneOf(params.get('receptionStatus'), RECEPTION_OPTIONS),
    paymentStatus: oneOf(params.get('paymentStatus'), PAYMENT_OPTIONS),
    search: (params.get('q') ?? '').trim(),
  };
}

/** Query params de la URL: solo los filtros con valor. */
export function filtersToQuery(filters: PurchaseListFilters): Params {
  const query: Params = {};
  if (filters.supplierId) query['supplierId'] = filters.supplierId;
  if (filters.dateFrom) query['dateFrom'] = filters.dateFrom;
  if (filters.dateTo) query['dateTo'] = filters.dateTo;
  if (filters.status) query['status'] = filters.status;
  if (filters.receptionStatus) query['receptionStatus'] = filters.receptionStatus;
  if (filters.paymentStatus) query['paymentStatus'] = filters.paymentStatus;
  if (filters.search.trim()) query['q'] = filters.search.trim();
  return query;
}

/** Parámetros de la API (sin paginación). */
export function filtersToApi(filters: PurchaseListFilters): PurchaseListParams {
  return {
    supplierId: filters.supplierId || undefined,
    dateFrom: filters.dateFrom || undefined,
    dateTo: filters.dateTo || undefined,
    status: filters.status || undefined,
    receptionStatus: filters.receptionStatus || undefined,
    paymentStatus: filters.paymentStatus || undefined,
    search: filters.search.trim() || undefined,
  };
}

export function hasActiveFilters(filters: PurchaseListFilters): boolean {
  return Object.keys(filtersToQuery(filters)).length > 0;
}

/** Rango incoherente: Desde posterior a Hasta (fechas ISO se comparan como texto). */
export function isRangeInvalid(filters: PurchaseListFilters): boolean {
  return !!filters.dateFrom && !!filters.dateTo && filters.dateFrom > filters.dateTo;
}

const formatDate = (iso: string): string => iso.split('-').reverse().join('/');

/** Texto de cada filtro activo, para mostrarlos cuando no hay resultados. */
export function describeFilters(filters: PurchaseListFilters, supplierName: string): string[] {
  const label = (options: { value: string; label: string }[], value: string): string =>
    options.find((o) => o.value === value)?.label ?? value;
  const parts: string[] = [];
  if (filters.search.trim()) parts.push(`Búsqueda: ${filters.search.trim()}`);
  if (filters.supplierId) parts.push(`Proveedor: ${supplierName || '…'}`);
  if (filters.dateFrom) parts.push(`Desde: ${formatDate(filters.dateFrom)}`);
  if (filters.dateTo) parts.push(`Hasta: ${formatDate(filters.dateTo)}`);
  if (filters.status) parts.push(`Estado: ${label(STATUS_OPTIONS, filters.status)}`);
  if (filters.receptionStatus) parts.push(`Recepción: ${label(RECEPTION_OPTIONS, filters.receptionStatus)}`);
  if (filters.paymentStatus) parts.push(`Pago: ${label(PAYMENT_OPTIONS, filters.paymentStatus)}`);
  return parts;
}
