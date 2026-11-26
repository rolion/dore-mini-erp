/** Reporte «Ingresos por venta»: pedidos entregados y pagados (API `/api/orders/paid-report/`). */
export interface PaidReportRow {
  id: string;
  code: string;
  orderDate: string;
  /** `null` si el pedido no tiene cliente o el módulo Clientes está deshabilitado. */
  customerName: string | null;
  total: string;
  balance: string;
}

export interface PaidReportTotals {
  ordersCount: number;
  total: string;
  balance: string;
}

export interface PaidReportPage {
  count: number;
  rows: PaidReportRow[];
  totals: PaidReportTotals;
}

export interface PaidReportFilters {
  /** `yyyy-MM-dd` o vacío. */
  dateFrom: string;
  dateTo: string;
  fiscalPeriodId: string;
}

export type PaidReportFormat = 'pdf' | 'xlsx';

export interface PaidReportRowDto {
  id: string;
  code: string;
  order_date: string;
  customer: { id: string; name: string } | null;
  total: string;
  balance: string;
}

export interface PaidReportPageDto {
  count: number;
  results: PaidReportRowDto[];
  totals: { orders_count: number; total: string; balance: string };
}

export function toPaidReportPage(dto: PaidReportPageDto): PaidReportPage {
  return {
    count: dto.count,
    rows: dto.results.map((row) => ({
      id: row.id,
      code: row.code,
      orderDate: row.order_date,
      customerName: row.customer?.name || null,
      total: row.total,
      balance: row.balance,
    })),
    totals: { ordersCount: dto.totals.orders_count, total: dto.totals.total, balance: dto.totals.balance },
  };
}
