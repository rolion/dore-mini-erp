/**
 * Reportes de pedidos con las mismas columnas y filtros: «Ingresos por venta» (`paid`, entregados y pagados) y
 * «Pedidos por cobrar» (`receivable`, con saldo pendiente). API `/api/orders/{paid|receivable}-report/`.
 */
export type SalesReportKind = 'paid' | 'receivable';

export interface SalesReportRow {
  id: string;
  code: string;
  orderDate: string;
  /** `null` si el pedido no tiene cliente o el módulo Clientes está deshabilitado. */
  customerName: string | null;
  total: string;
  balance: string;
}

export interface SalesReportTotals {
  ordersCount: number;
  total: string;
  balance: string;
}

export interface SalesReportPage {
  count: number;
  rows: SalesReportRow[];
  totals: SalesReportTotals;
}

export interface SalesReportFilters {
  /** `yyyy-MM-dd` o vacío. */
  dateFrom: string;
  dateTo: string;
  fiscalPeriodId: string;
}

export type SalesReportFormat = 'pdf' | 'xlsx';

export interface SalesReportRowDto {
  id: string;
  code: string;
  order_date: string;
  customer: { id: string; name: string } | null;
  total: string;
  balance: string;
}

export interface SalesReportPageDto {
  count: number;
  results: SalesReportRowDto[];
  totals: { orders_count: number; total: string; balance: string };
}

export function toSalesReportPage(dto: SalesReportPageDto): SalesReportPage {
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
