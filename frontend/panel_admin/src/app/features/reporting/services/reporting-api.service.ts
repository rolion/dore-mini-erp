import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import {
  CategoryExpense,
  ChannelReport,
  CustomersReport,
  DashboardSummary,
  ExpensesReport,
  Period,
  PeriodSelection,
  PendingReport,
  ProductsReport,
  SalesReport,
} from '../models/report';

export const NETWORK_ERROR_MESSAGE = 'No se pudo conectar con el servidor.';
export const GENERIC_ERROR_MESSAGE = 'No se pudo cargar.';
export const INVALID_PERIOD_MESSAGE = 'El periodo no es válido.';

// --- Formas de respuesta de la API (snake_case) -------------------------------------------------------------

interface PeriodDto {
  kind: Period['kind'];
  date_from: string;
  date_to: string;
}

interface DashboardDto {
  period: PeriodDto;
  sales_total: string;
  orders_count: number;
  average_ticket: string | null;
  expenses_total: string;
  estimated_profit: string;
  pending_delivery_count: number;
  pending_collection_count: number;
  pending_collection_balance: string;
  sales_criteria: string;
}

interface SalesDto {
  period: PeriodDto;
  total: string;
  orders_count: number;
  average_ticket: string | null;
  criteria: string;
}

interface ExpensesDto {
  period: PeriodDto;
  total: string;
  categories: { category_id: string; name: string; active: boolean; total: string }[];
}

interface ChannelsDto {
  period: PeriodDto;
  channels: { sales_channel: ChannelReport['channels'][number]['salesChannel']; orders_count: number; total: string }[];
}

interface ProductsDto {
  period: PeriodDto;
  limit: number;
  products: { product_id: string; product_name: string; units: number; amount: string }[];
}

interface CustomersDto {
  period: PeriodDto;
  limit: number;
  customers: { customer_id: string; name: string; orders_count: number; total: string }[];
}

interface PendingRowDto {
  id: string;
  order_date: string;
  customer: { id: string; name: string } | null;
  total: string;
  status: PendingReport['delivery']['rows'][number]['status'];
  payment_status: PendingReport['delivery']['rows'][number]['paymentStatus'];
  expected_delivery_date?: string | null;
  balance?: string;
}

interface PendingDto {
  delivery: { count: number; rows: PendingRowDto[] };
  collection: { count: number; balance_total: string; rows: PendingRowDto[] };
}

// --- Mapeos -------------------------------------------------------------------------------------------------

function toPeriod(dto: PeriodDto): Period {
  return { kind: dto.kind, dateFrom: dto.date_from, dateTo: dto.date_to };
}

function toCategory(dto: ExpensesDto['categories'][number]): CategoryExpense {
  return { categoryId: dto.category_id, name: dto.name, active: dto.active, total: dto.total };
}

function toError(err: HttpErrorResponse): Error {
  if (err.status === 0) return new Error(NETWORK_ERROR_MESSAGE);
  if (err.status === 400) return new Error(INVALID_PERIOD_MESSAGE);
  return new Error(GENERIC_ERROR_MESSAGE);
}

/** `period`/`date_from`/`date_to` según lo pedido; el servidor devuelve las fechas efectivas. */
export function periodParams(selection: PeriodSelection): HttpParams {
  if (selection.kind === 'range') {
    return new HttpParams().set('date_from', selection.dateFrom).set('date_to', selection.dateTo);
  }
  return new HttpParams().set('period', selection.kind);
}

@Injectable({
  providedIn: 'root',
})
export class ReportingApiService {
  private http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/reports/`;

  dashboard(selection: PeriodSelection): Observable<DashboardSummary> {
    return this.get<DashboardDto, DashboardSummary>('dashboard/', selection, (dto) => ({
      period: toPeriod(dto.period),
      salesTotal: dto.sales_total,
      ordersCount: dto.orders_count,
      averageTicket: dto.average_ticket,
      expensesTotal: dto.expenses_total,
      estimatedProfit: dto.estimated_profit,
      pendingDeliveryCount: dto.pending_delivery_count,
      pendingCollectionCount: dto.pending_collection_count,
      pendingCollectionBalance: dto.pending_collection_balance,
      salesCriteria: dto.sales_criteria,
    }));
  }

  sales(selection: PeriodSelection): Observable<SalesReport> {
    return this.get<SalesDto, SalesReport>('sales/', selection, (dto) => ({
      period: toPeriod(dto.period),
      total: dto.total,
      ordersCount: dto.orders_count,
      averageTicket: dto.average_ticket,
      criteria: dto.criteria,
    }));
  }

  expenses(selection: PeriodSelection): Observable<ExpensesReport> {
    return this.get<ExpensesDto, ExpensesReport>('expenses/', selection, (dto) => ({
      period: toPeriod(dto.period),
      total: dto.total,
      categories: dto.categories.map(toCategory),
    }));
  }

  salesByChannel(selection: PeriodSelection): Observable<ChannelReport> {
    return this.get<ChannelsDto, ChannelReport>('sales-by-channel/', selection, (dto) => ({
      period: toPeriod(dto.period),
      channels: dto.channels.map((c) => ({ salesChannel: c.sales_channel, ordersCount: c.orders_count, total: c.total })),
    }));
  }

  topProducts(selection: PeriodSelection): Observable<ProductsReport> {
    return this.get<ProductsDto, ProductsReport>('top-products/', selection, (dto) => ({
      period: toPeriod(dto.period),
      limit: dto.limit,
      products: dto.products.map((p) => ({
        productId: p.product_id,
        productName: p.product_name,
        units: p.units,
        amount: p.amount,
      })),
    }));
  }

  topCustomers(selection: PeriodSelection): Observable<CustomersReport> {
    return this.get<CustomersDto, CustomersReport>('top-customers/', selection, (dto) => ({
      period: toPeriod(dto.period),
      limit: dto.limit,
      customers: dto.customers.map((c) => ({
        customerId: c.customer_id,
        name: c.name,
        ordersCount: c.orders_count,
        total: c.total,
      })),
    }));
  }

  /** Estado actual de los pedidos pendientes: no depende de ningún periodo. */
  pending(): Observable<PendingReport> {
    return this.http.get<PendingDto>(`${this.baseUrl}pending/`).pipe(
      map(
        (dto): PendingReport => ({
          delivery: {
            count: dto.delivery.count,
            rows: dto.delivery.rows.map((r) => ({
              id: r.id,
              orderDate: r.order_date,
              customer: r.customer,
              expectedDeliveryDate: r.expected_delivery_date ?? null,
              status: r.status,
              paymentStatus: r.payment_status,
              total: r.total,
            })),
          },
          collection: {
            count: dto.collection.count,
            balanceTotal: dto.collection.balance_total,
            rows: dto.collection.rows.map((r) => ({
              id: r.id,
              orderDate: r.order_date,
              customer: r.customer,
              total: r.total,
              balance: r.balance ?? '0.00',
              status: r.status,
              paymentStatus: r.payment_status,
            })),
          },
        }),
      ),
      catchError((err: HttpErrorResponse) => throwError(() => toError(err))),
    );
  }

  private get<Dto, Result>(path: string, selection: PeriodSelection, map_: (dto: Dto) => Result): Observable<Result> {
    return this.http.get<Dto>(`${this.baseUrl}${path}`, { params: periodParams(selection) }).pipe(
      map(map_),
      catchError((err: HttpErrorResponse) => throwError(() => toError(err))),
    );
  }
}
