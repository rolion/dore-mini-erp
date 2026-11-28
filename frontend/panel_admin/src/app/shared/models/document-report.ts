/**
 * Reportes de documentos con las mismas columnas y filtros (fecha inicio, fecha fin y período fiscal):
 * ventas «Ingresos por venta» (`paid`) y «Pedidos por cobrar» (`receivable`); compras «Compras pagadas»
 * (`purchases-paid`) y «Compras por pagar» (`purchases-payable`). Odontología («Proformas por cobrar» y «Proformas
 * pagadas») usa los mismos filtros de fecha pero sin período fiscal y con columnas Doctor y Monto (`doctorColumn`).
 */
export type DocumentReportKind =
  | 'paid' | 'receivable' | 'purchases-paid' | 'purchases-payable' | 'dental-receivable' | 'dental-paid';

export const DOCUMENT_REPORT_KINDS: readonly DocumentReportKind[] = [
  'paid', 'receivable', 'purchases-paid', 'purchases-payable', 'dental-receivable', 'dental-paid',
];

/** Qué cambia entre reportes: endpoint, textos, etiquetas de columna y destino del enlace al documento. */
export interface DocumentReportConfig {
  /** Ruta de la API bajo `/api/`, con barra final. */
  apiPath: string;
  titleKey: string;
  subtitleKey: string;
  emptyKey: string;
  documentColumnKey: string;
  totalsKey: string;
  partyColumnKey: string;
  /** Prefijo de la ruta del detalle: se le añade `/<id>`. */
  detailRoute: string;
  fileName: string;
  /** Columnas Doctor y un único Monto en lugar de Total y Saldo; sin filtro de período fiscal. */
  doctorColumn?: boolean;
  /** Cabecera de la columna Monto (solo con `doctorColumn`). */
  amountColumnKey?: string;
}

export const DOCUMENT_REPORT_CONFIG: Record<DocumentReportKind, DocumentReportConfig> = {
  paid: {
    apiPath: 'orders/paid-report/',
    titleKey: 'SALES.PAID_REPORT.TITLE',
    subtitleKey: 'SALES.PAID_REPORT.SUBTITLE',
    emptyKey: 'SALES.PAID_REPORT.EMPTY',
    documentColumnKey: 'SALES.PAID_REPORT.COL_ORDER',
    totalsKey: 'SALES.PAID_REPORT.TOTALS',
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
    totalsKey: 'SALES.PAID_REPORT.TOTALS',
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
    totalsKey: 'PURCHASES.PAID_REPORT.TOTALS',
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
    totalsKey: 'PURCHASES.PAID_REPORT.TOTALS',
    partyColumnKey: 'PURCHASES.PAID_REPORT.COL_SUPPLIER',
    detailRoute: '/pocketbiz/purchases',
    fileName: 'compras-por-pagar',
  },
  'dental-receivable': {
    apiPath: 'dentistry/reports/proformas/receivable/',
    titleKey: 'DENTISTRY.REPORTS.RECEIVABLE_TITLE',
    subtitleKey: 'DENTISTRY.REPORTS.RECEIVABLE_SUBTITLE',
    emptyKey: 'DENTISTRY.REPORTS.RECEIVABLE_EMPTY',
    documentColumnKey: 'DENTISTRY.REPORTS.COL_PROFORMA',
    totalsKey: 'DENTISTRY.REPORTS.TOTALS',
    partyColumnKey: 'DENTISTRY.REPORTS.COL_PATIENT',
    detailRoute: '/pocketbiz/dentistry/proformas',
    fileName: 'proformas-por-cobrar',
    doctorColumn: true,
    amountColumnKey: 'DENTISTRY.REPORTS.COL_AMOUNT_RECEIVABLE',
  },
  'dental-paid': {
    apiPath: 'dentistry/reports/proformas/paid/',
    titleKey: 'DENTISTRY.REPORTS.PAID_TITLE',
    subtitleKey: 'DENTISTRY.REPORTS.PAID_SUBTITLE',
    emptyKey: 'DENTISTRY.REPORTS.PAID_EMPTY',
    documentColumnKey: 'DENTISTRY.REPORTS.COL_PROFORMA',
    totalsKey: 'DENTISTRY.REPORTS.TOTALS',
    partyColumnKey: 'DENTISTRY.REPORTS.COL_PATIENT',
    detailRoute: '/pocketbiz/dentistry/proformas',
    fileName: 'proformas-pagadas',
    doctorColumn: true,
    amountColumnKey: 'DENTISTRY.REPORTS.COL_AMOUNT_PAID',
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
  /** Solo reportes con `doctorColumn`. */
  doctorName?: string | null;
  amount?: string;
}

export interface DocumentReportTotals {
  ordersCount: number;
  total: string;
  balance: string;
  /** Solo reportes con `doctorColumn`: suma de la columna Monto. */
  amount?: string;
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
  total?: string;
  balance?: string;
  doctor?: { id: string; name: string } | null;
  amount?: string;
}

export interface DocumentReportPageDto {
  count: number;
  results: DocumentReportRowDto[];
  totals: { orders_count?: number; count?: number; total?: string; balance?: string; amount?: string };
}

export function toDocumentReportPage(dto: DocumentReportPageDto): DocumentReportPage {
  return {
    count: dto.count,
    rows: dto.results.map((row) => ({
      id: row.id,
      code: row.code,
      orderDate: row.order_date,
      customerName: row.customer?.name || null,
      total: row.total ?? '0.00',
      balance: row.balance ?? '0.00',
      ...(row.amount !== undefined ? { doctorName: row.doctor?.name || null, amount: row.amount } : {}),
    })),
    totals: {
      ordersCount: dto.totals.orders_count ?? dto.totals.count ?? 0,
      total: dto.totals.total ?? '0.00',
      balance: dto.totals.balance ?? '0.00',
      ...(dto.totals.amount !== undefined ? { amount: dto.totals.amount } : {}),
    },
  };
}
