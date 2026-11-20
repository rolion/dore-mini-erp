import { PostingIssue } from '../../../shared/models/receivable';

/** Campos de destino del mapeo (claves exactas del contrato de la API). */
export type ImportField =
  | 'sale_date'
  | 'product_name'
  | 'quantity'
  | 'unit_price'
  | 'sale_number'
  | 'customer_name'
  | 'payment_method'
  | 'sales_channel'
  | 'supplier_name'
  | 'unit_cost'
  | 'discount'
  | 'category'
  | 'notes';

export interface ImportFieldDef {
  key: ImportField;
  required: boolean;
  /** Clave de traducción de la etiqueta (literal, para que `i18n:check` la verifique). */
  labelKey: string;
}

export const IMPORT_FIELDS: readonly ImportFieldDef[] = [
  { key: 'sale_date', required: true, labelKey: 'DATA_IMPORT.FIELDS.SALE_DATE' },
  { key: 'product_name', required: true, labelKey: 'DATA_IMPORT.FIELDS.PRODUCT_NAME' },
  { key: 'quantity', required: true, labelKey: 'DATA_IMPORT.FIELDS.QUANTITY' },
  { key: 'unit_price', required: true, labelKey: 'DATA_IMPORT.FIELDS.UNIT_PRICE' },
  { key: 'sale_number', required: false, labelKey: 'DATA_IMPORT.FIELDS.SALE_NUMBER' },
  { key: 'customer_name', required: false, labelKey: 'DATA_IMPORT.FIELDS.CUSTOMER_NAME' },
  { key: 'payment_method', required: false, labelKey: 'DATA_IMPORT.FIELDS.PAYMENT_METHOD' },
  { key: 'sales_channel', required: false, labelKey: 'DATA_IMPORT.FIELDS.SALES_CHANNEL' },
  { key: 'supplier_name', required: false, labelKey: 'DATA_IMPORT.FIELDS.SUPPLIER_NAME' },
  { key: 'unit_cost', required: false, labelKey: 'DATA_IMPORT.FIELDS.UNIT_COST' },
  { key: 'discount', required: false, labelKey: 'DATA_IMPORT.FIELDS.DISCOUNT' },
  { key: 'category', required: false, labelKey: 'DATA_IMPORT.FIELDS.CATEGORY' },
  { key: 'notes', required: false, labelKey: 'DATA_IMPORT.FIELDS.NOTES' },
];

export type ImportMapping = Record<ImportField, string | null>;

export type PaymentMethodCode = 'CASH' | 'QR' | 'BANK_TRANSFER' | 'CARD' | 'OTHER';
export type SalesChannelCode = 'WHATSAPP' | 'FACEBOOK' | 'INSTAGRAM' | 'STORE' | 'FAIR' | 'OTHER';
export type ProductCategoryCode = 'raw_material' | 'packaging' | 'intermediate' | 'finished' | 'merchandise';
export type DateFormatCode = 'dmy' | 'mdy' | 'ymd';

/** Opciones con etiqueta traducible (claves literales). */
export const PAYMENT_METHOD_OPTIONS: readonly { value: PaymentMethodCode; labelKey: string }[] = [
  { value: 'CASH', labelKey: 'DATA_IMPORT.PAYMENT.CASH' },
  { value: 'QR', labelKey: 'DATA_IMPORT.PAYMENT.QR' },
  { value: 'BANK_TRANSFER', labelKey: 'DATA_IMPORT.PAYMENT.BANK_TRANSFER' },
  { value: 'CARD', labelKey: 'DATA_IMPORT.PAYMENT.CARD' },
  { value: 'OTHER', labelKey: 'DATA_IMPORT.PAYMENT.OTHER' },
];

export const SALES_CHANNEL_OPTIONS: readonly { value: SalesChannelCode; labelKey: string }[] = [
  { value: 'WHATSAPP', labelKey: 'DATA_IMPORT.CHANNEL.WHATSAPP' },
  { value: 'FACEBOOK', labelKey: 'DATA_IMPORT.CHANNEL.FACEBOOK' },
  { value: 'INSTAGRAM', labelKey: 'DATA_IMPORT.CHANNEL.INSTAGRAM' },
  { value: 'STORE', labelKey: 'DATA_IMPORT.CHANNEL.STORE' },
  { value: 'FAIR', labelKey: 'DATA_IMPORT.CHANNEL.FAIR' },
  { value: 'OTHER', labelKey: 'DATA_IMPORT.CHANNEL.OTHER' },
];

export const PRODUCT_CATEGORY_OPTIONS: readonly { value: ProductCategoryCode; labelKey: string }[] = [
  { value: 'finished', labelKey: 'DATA_IMPORT.CATEGORY.FINISHED' },
  { value: 'packaging', labelKey: 'DATA_IMPORT.CATEGORY.PACKAGING' },
  { value: 'merchandise', labelKey: 'DATA_IMPORT.CATEGORY.MERCHANDISE' },
  { value: 'intermediate', labelKey: 'DATA_IMPORT.CATEGORY.INTERMEDIATE' },
  { value: 'raw_material', labelKey: 'DATA_IMPORT.CATEGORY.RAW_MATERIAL' },
];

export const DATE_FORMAT_OPTIONS: readonly { value: DateFormatCode; labelKey: string }[] = [
  { value: 'dmy', labelKey: 'DATA_IMPORT.DATE.DMY' },
  { value: 'mdy', labelKey: 'DATA_IMPORT.DATE.MDY' },
  { value: 'ymd', labelKey: 'DATA_IMPORT.DATE.YMD' },
];

export interface ImportOptions {
  inferProducts: boolean;
  inferCustomers: boolean;
  inferInventory: boolean;
  inferAccounting: boolean;
  defaultPaymentMethod: PaymentMethodCode;
  defaultSalesChannel: SalesChannelCode;
  defaultCategory: ProductCategoryCode;
  warehouseId: string | null;
  dateFormat: DateFormatCode;
}

export interface ImportRequest {
  mapping: ImportMapping;
  options: ImportOptions;
}

export interface ImportWarehouse {
  id: string;
  name: string;
  isDefault: boolean;
}

export interface ImportCapabilities {
  customers: boolean;
  inventory: boolean;
  purchases: boolean;
  accounting: boolean;
  costing: boolean;
  warehouses: ImportWarehouse[];
  paymentMethods: string[];
  salesChannels: string[];
}

export interface ImportUpload {
  id: string;
  filename: string;
  rowCount: number;
  headers: string[];
  sampleRows: string[][];
  suggestedMapping: ImportMapping;
  capabilities: ImportCapabilities;
}

export interface ImportProblem {
  row: number;
  saleKey: string;
  field: string;
  code: string;
  message: string;
}

export interface ImportPreview {
  salesTotal: number;
  linesTotal: number;
  toCreate: number;
  alreadyImported: number;
  withErrors: number;
  newProducts: number;
  existingProducts: number;
  newCustomers: number;
  existingCustomers: number;
  purchasesToCreate: number;
  unitsToBuy: number;
  withoutPosting: number;
  problems: ImportProblem[];
  problemsTotal: number;
}

export interface ImportCounts {
  created: number;
  skipped: number;
  failed: number;
  withoutPosting: number;
}

export type ImportRunStatus = 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | (string & {});

/** Motivo por el que la importación se detuvo (lo informa el servidor). */
export interface ImportFailure {
  code: string;
  message: string;
}

export interface ImportResult {
  id: string;
  status: ImportRunStatus;
  counts: ImportCounts;
  /** Ventas ya tratadas y ventas por tratar (0 mientras la corrida está en cola). */
  processed: number;
  total: number;
  failure: ImportFailure | null;
}

/** La importación sigue en el servidor (en cola o en curso). */
export function isActiveRun(status: ImportRunStatus): boolean {
  return status === 'QUEUED' || status === 'RUNNING';
}

export interface ImportRunSummary {
  id: string;
  filename: string;
  status: ImportRunStatus;
  createdAt: string;
  createdByName: string;
  rowCount: number;
  counts: ImportCounts;
  processed: number;
  total: number;
  failure: ImportFailure | null;
}

export interface ImportRunDetail extends ImportRunSummary {
  options: Record<string, unknown>;
}

export type ImportRowStatus = 'CREATED' | 'SKIPPED_DUPLICATE' | 'FAILED' | 'CREATED_WITHOUT_POSTING';

export const IMPORT_ROW_STATUSES: readonly ImportRowStatus[] = [
  'CREATED',
  'SKIPPED_DUPLICATE',
  'CREATED_WITHOUT_POSTING',
  'FAILED',
];

export interface ImportRow {
  row: number;
  saleKey: string;
  status: ImportRowStatus;
  code: string;
  message: string;
  orderId: string | null;
}

export type ImportFieldErrors = Record<string, string[]>;

/** Error de la API de importación con lo que la pantalla necesita para explicarlo sin perder el estado. */
export class ImportApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string = '',
    readonly fieldErrors: ImportFieldErrors = {},
    readonly issues: PostingIssue[] = [],
  ) {
    super(message);
    this.name = 'ImportApiError';
  }

  /** Mensajes de campo aplanados (para mostrarlos en una lista). */
  get fieldMessages(): string[] {
    return Object.values(this.fieldErrors).flat();
  }
}

/** UUID v4 para la clave de idempotencia (con respaldo si `crypto.randomUUID` no existe). */
export function newUuid(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (char) => {
    const n = Math.floor(Math.random() * 16);
    return (char === 'x' ? n : (n & 0x3) | 0x8).toString(16);
  });
}
