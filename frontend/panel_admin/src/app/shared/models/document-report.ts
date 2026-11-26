/**
 * Reportes de documentos con las mismas columnas y filtros (fecha inicio, fecha fin y período fiscal):
 * ventas «Ingresos por venta» (`paid`) y «Pedidos por cobrar» (`receivable`); compras «Compras pagadas»
 * (`purchases-paid`) y «Compras por pagar» (`purchases-payable`).
 */
export type DocumentReportKind = 'paid' | 'receivable' | 'purchases-paid' | 'purchases-payable';

export const DOCUMENT_REPORT_KINDS: readonly DocumentReportKind[] = ['paid', 'receivable', 'purchases-paid', 'purchases-payable'];

/** Qué cambia entre reportes: endpoint, textos, etiquetas de columna y destino del enlace al documento. */
export interface DocumentReportConfig {
  /** Ruta de la API bajo `/api/`, con barra final. */
  apiPath: string;
  titleKey: string;
  subtitleKey: string;
  emptyKey: string;
  documentColumnKey: string;
  partyColumnKey: string;
  /** Prefijo de la ruta del detalle: se le añade `/<id>`. */
  detailRoute: string;
  fileName: string;
}

export const DOCUMENT_REPORT_CONFIG: Record<DocumentReportKind, DocumentReportConfig> = {
  paid: {
    apiPath: 'orders/paid-report/',
    titleKey: 'SALES.PAID_REPORT.TITLE',
    subtitleKey: 'SALES.PAID_REPORT.SUBTITLE',
    emptyKey: 'SALES.PAID_REPORT.EMPTY',
    documentColumnKey: 'SALES.PAID_REPORT.COL_ORDER',
    partyColumnKey: 'SALES.PAID_REPORT.COL_CUSTOMER',
    detailRoute: '/pocketbiz/sales/orders',
    fileName: 'ingresos-por-venta',
  },
  receivable: {
    apiPath: 'orders/receivable-report/',
    titleKey: 'SALES.RECEIVABLE_REPORT.TITLE',
    subtitleKey: 'SALES.RECEIVABLE_REPORT.SUBTITLE',
    emptyKey: 'SALES.RECEIVABLE_REPORT.EMPTY',
    documentColumnKey: 'SALES.PAID_REPORT.COL_ORDER',
    partyColumnKey: 'SALES.PAID_REPORT.COL_CUSTOMER',
    detailRoute: '/pocketbiz/sales/orders',
    fileName: 'pedidos-por-cobrar',
  },
  'purchases-paid': {
    apiPath: 'purchases/paid-report/',
    titleKey: 'PURCHASES.PAID_REPORT.TITLE',
    subtitleKey: 'PURCHASES.PAID_REPORT.SUBTITLE',
    emptyKey: 'PURCHASES.PAID_REPORT.EMPTY',
    documentColumnKey: 'PURCHASES.PAID_REPORT.COL_PURCHASE',
    partyColumnKey: 'PURCHASES.PAID_REPORT.COL_SUPPLIER',
    detailRoute: '/pocketbiz/purchases',
    fileName: 'compras-pagadas',
  },
  'purchases-payable': {
    apiPath: 'purchases/payable-report/',
    titleKey: 'PURCHASES.PAYABLE_REPORT.TITLE',
    subtitleKey: 'PURCHASES.PAYABLE_REPORT.SUBTITLE',
    emptyKey: 'PURCHASES.PAYABLE_REPORT.EMPTY',
    documentColumnKey: 'PURCHASES.PAID_REPORT.COL_PURCHASE',
    partyColumnKey: 'PURCHASES.PAID_REPORT.COL_SUPPLIER',
    detailRoute: '/pocketbiz/purchases',
    fileName: 'compras-por-pagar',
  },
};

export interface DocumentReportRow {
  id: string;
  code: string;
  orderDate: string;
  /** Cliente o proveedor; `null` si no hay o el módulo Clientes está deshabilitado. */
  customerName: string | null;
  total: string;
  balance: string;
}

export interface DocumentReportTotals {
  ordersCount: number;
  total: string;
  balance: string;
}

export interface DocumentReportPage {
  count: number;
  rows: DocumentReportRow[];
  totals: DocumentReportTotals;
}

export interface DocumentReportFilters {
  /** `yyyy-MM-dd` o vacío. */
  dateFrom: string;
  dateTo: string;
  fiscalPeriodId: string;
}

export type DocumentReportFormat = 'pdf' | 'xlsx';

export interface DocumentReportRowDto {
  id: string;
  code: string;
  order_date: string;
  customer: { id: string; name: string } | null;
  total: string;
  balance: string;
}

export interface DocumentReportPageDto {
  count: number;
  results: DocumentReportRowDto[];
  totals: { orders_count: number; total: string; balance: string };
}

export function toDocumentReportPage(dto: DocumentReportPageDto): DocumentReportPage {
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
