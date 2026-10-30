export type ReceiptStatus = 'confirmed' | 'reverted';

export const RECEIPT_STATUS_LABELS: Readonly<Record<ReceiptStatus, string>> = {
  confirmed: 'Confirmada',
  reverted: 'Revertida',
};

export const RECEIPT_STATUS_CLASSES: Readonly<Record<ReceiptStatus, string>> = {
  confirmed: 'col-green',
  reverted: 'col-orange',
};

export interface ReceiptSummary {
  id: string;
  reference: string;
  receiptDate: string;
  status: ReceiptStatus;
  userName: string;
  linesCount: number;
}

/** Modo con que se confirmó la recepción; `null` en recepciones antiguas sin almacén (modo desconocido). */
export type ReceiptInventoryMode = 'inventory' | 'documental';

export const SIN_ENTRADA_LABEL = 'Sin control de stock · sin entrada';
export const DOCUMENTAL_LABEL = 'Recepción documental, sin movimiento de inventario';

export interface ReceiptLine {
  itemId: string;
  productId: string;
  productName: string;
  unitAbbreviation: string;
  quantity: string;
  /** `null` salvo en modo `inventory`: si la línea generó una entrada de stock. */
  stockEntry: boolean | null;
}

export interface ReceiptMovement {
  id: string;
  reference: string;
  productName: string;
  warehouseName: string;
  quantity: string;
  unitAbbreviation: string;
}

export interface ReceiptWarehouse {
  id: string;
  name: string;
}

export interface Receipt {
  id: string;
  reference: string;
  purchase: { id: string; reference: string };
  receiptDate: string;
  status: ReceiptStatus;
  userName: string;
  createdAt: string;
  warehouse: ReceiptWarehouse | null;
  lines: ReceiptLine[];
  inventoryMode: ReceiptInventoryMode | null;
  /** Estado actual del módulo Inventario (solo para decidir si hay enlace a Movimientos). */
  inventoryAvailable: boolean;
  /** `null` si la recepción fue documental; `[]` si no generó entradas. */
  movements: ReceiptMovement[] | null;
}

export interface ReceptionWarehouse {
  id: string;
  name: string;
  isDefault: boolean;
}

/** Línea del formulario: cantidades de la compra y lo que falta recibir. */
export interface ReceptionFormLine {
  itemId: string;
  productId: string;
  productName: string;
  unitAbbreviation: string;
  allowsFractions: boolean;
  tracksStock: boolean;
  ordered: string;
  received: string;
  pending: string;
}

export interface ReceptionForm {
  inventoryEnabled: boolean;
  warehouses: ReceptionWarehouse[];
  warehouseId: string | null;
  lines: ReceptionFormLine[];
}

export interface ReceiptLineInput {
  itemId: string;
  quantity: string;
}

export interface ReceiptInput {
  /** Generado al abrir el formulario y reutilizado en los reintentos (idempotencia). */
  receiptId: string;
  receiptDate: string;
  warehouseId: string | null;
  lines: ReceiptLineInput[];
}

/** Errores 400 por campo de cabecera y por línea (en el orden en que se enviaron las líneas). */
export interface ReceiptFieldErrors {
  receiptDate?: string;
  warehouseId?: string;
  /** Mensaje general de `lines` (p. ej. «Indica al menos un producto recibido.»). */
  linesMessage?: string;
  lines: { itemId?: string; quantity?: string }[];
}

export class ReceiptApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly fieldErrors: ReceiptFieldErrors = { lines: [] },
  ) {
    super(message);
    this.name = 'ReceiptApiError';
  }
}

/** Forma de respuesta de la API (snake_case). */
export interface ReceiptSummaryDto {
  id: string;
  reference: string;
  receipt_date: string;
  status: ReceiptStatus;
  user_name: string;
  lines_count: number;
}

export interface ReceiptDto {
  id: string;
  reference: string;
  purchase: { id: string; reference: string };
  receipt_date: string;
  status: ReceiptStatus;
  user_name: string;
  created_at: string;
  warehouse: ReceiptWarehouse | null;
  lines: {
    item_id: string;
    product: { id: string; name: string };
    unit: { abbreviation: string };
    quantity: string;
    stock_entry?: boolean | null;
  }[];
  inventory_mode?: ReceiptInventoryMode | null;
  inventory_available?: boolean;
  movements:
    | {
        id: string;
        product: { id: string; name: string };
        warehouse: { id: string; name: string };
        quantity: string;
        unit: { abbreviation: string };
        reference?: string;
      }[]
    | null;
}

export interface ReceptionFormDto {
  inventory_enabled: boolean;
  warehouses: { id: string; name: string; is_default: boolean }[];
  warehouse_id: string | null;
  lines: {
    item_id: string;
    product: { id: string; name: string };
    unit: { abbreviation: string };
    allows_fractions: boolean;
    tracks_stock: boolean;
    ordered: string;
    received: string;
    pending: string;
  }[];
}
