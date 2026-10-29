/** Moneda fija e informativa de las compras. */
export const PURCHASE_CURRENCY = 'BOB';
export const MAX_ITEMS = 200;
export const REFERENCE_MAX_LENGTH = 100;
export const NOTES_MAX_LENGTH = 2000;

export type PurchaseStatus = 'draft';

export const PURCHASE_STATUS_LABELS: Readonly<Record<PurchaseStatus, string>> = {
  draft: 'Borrador',
};

export interface PurchaseSupplier {
  id: string;
  name: string;
}

export interface PurchaseDetailSupplier extends PurchaseSupplier {
  active: boolean;
}

/** Línea guardada. Importes y cantidades viajan como texto decimal para no perder precisión. */
export interface PurchaseItem {
  id: string;
  productId: string;
  productName: string;
  unitAbbreviation: string;
  quantity: string;
  unitPrice: string;
  subtotal: string;
}

export interface Purchase {
  id: string;
  supplier: PurchaseDetailSupplier;
  purchaseDate: string;
  externalReference: string;
  notes: string;
  status: PurchaseStatus;
  currency: string;
  editable: boolean;
  items: PurchaseItem[];
  total: string;
  createdAt: string;
  updatedAt: string;
}

export interface PurchaseSummary {
  id: string;
  purchaseDate: string;
  supplier: PurchaseSupplier;
  externalReference: string;
  total: string;
  currency: string;
  status: PurchaseStatus;
  itemsCount: number;
}

/** Línea que se envía al guardar (el servidor aporta nombre, unidad y subtotal). */
export interface PurchaseItemInput {
  productId: string;
  quantity: string;
  unitPrice: string;
}

export interface PurchaseInput {
  supplierId: string;
  purchaseDate: string;
  externalReference: string;
  notes: string;
  items: PurchaseItemInput[];
}

export interface PurchaseListParams {
  supplierId?: string;
  /** Página base 1. */
  page?: number;
  pageSize?: number;
}

/** Forma de respuesta de la API (snake_case). */
export interface PurchaseItemDto {
  id: string;
  product_id: string;
  product_name: string;
  unit_abbreviation: string;
  quantity: string;
  unit_price: string;
  subtotal: string;
}

export interface PurchaseDto {
  id: string;
  supplier: PurchaseDetailSupplier;
  purchase_date: string;
  external_reference: string;
  notes: string;
  status: PurchaseStatus;
  currency: string;
  editable: boolean;
  items: PurchaseItemDto[];
  total: string;
  created_at: string;
  updated_at: string;
}

export interface PurchaseSummaryDto {
  id: string;
  purchase_date: string;
  supplier: PurchaseSupplier;
  external_reference: string;
  total: string;
  currency: string;
  status: PurchaseStatus;
  items_count: number;
}

export type HeaderField = 'supplierId' | 'purchaseDate' | 'externalReference' | 'notes';
export type ItemField = 'productId' | 'quantity' | 'unitPrice';

/** Errores de una línea por campo, en el orden en que se enviaron las líneas. */
export type ItemErrors = Partial<Record<ItemField, string>>;

export interface PurchaseFieldErrors {
  header: Partial<Record<HeaderField, string>>;
  items: ItemErrors[];
  /** Mensaje general de `items` (p. ej. demasiadas líneas). */
  itemsMessage?: string;
}

export class PurchaseApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly fieldErrors: PurchaseFieldErrors = { header: {}, items: [] },
  ) {
    super(message);
    this.name = 'PurchaseApiError';
  }
}

/** Fecha local de hoy como `YYYY-MM-DD`. */
export function todayIso(now: Date = new Date()): string {
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${now.getFullYear()}-${month}-${day}`;
}
