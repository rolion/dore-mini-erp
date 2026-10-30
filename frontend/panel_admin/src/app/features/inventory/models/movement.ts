export type MovementKind = 'in' | 'out';
export type MovementStatus = 'confirmed' | 'reversed';

export const MOVEMENT_KIND_LABELS: Record<MovementKind, string> = { in: 'Entrada', out: 'Salida' };
/** Clase de origen cuyas salidas se muestran como «Salida por venta». */
export const SALES_ORDER_SOURCE = 'sales_order';

/** Clase de origen cuyas entradas se muestran como «Entrada por compra». */
export const PURCHASE_RECEIPT_SOURCE = 'purchase_receipt';

/** Etiqueta del tipo de movimiento: «Salida por venta» (pedido) y «Entrada por compra» (recepción). */
export function movementTypeLabel(movement: { kind: MovementKind; source: { type: string } | null }): string {
  if (movement.kind === 'out' && movement.source?.type === SALES_ORDER_SOURCE) return 'Salida por venta';
  if (movement.kind === 'in' && movement.source?.type === PURCHASE_RECEIPT_SOURCE) return 'Entrada por compra';
  return MOVEMENT_KIND_LABELS[movement.kind];
}

export const MOVEMENT_STATUS_LABELS: Record<MovementStatus, string> = {
  confirmed: 'Confirmado',
  reversed: 'Revertido',
};

/** Clases de documento de origen que conoce el servidor, con la etiqueta del filtro. */
export const SOURCE_TYPE_OPTIONS: readonly { value: string; label: string }[] = [
  { value: 'sales_order', label: 'Pedido de venta' },
  { value: 'purchase_receipt', label: 'Recepción de compra' },
  { value: 'inventory_adjustment', label: 'Ajuste de inventario' },
  { value: 'inventory_opening', label: 'Apertura de existencias' },
  { value: 'none', label: 'Sin documento' },
];

/** Pantalla de destino por clase de origen; solo existen las de módulos ya construidos. */
export const SOURCE_ROUTES: Readonly<Record<string, (id: string) => string[]>> = {
  sales_order: (id) => ['/pocketbiz/sales/orders', id],
  inventory_adjustment: (id) => ['/pocketbiz/inventory/adjustments', id],
};

export interface MovementSource {
  type: string;
  label: string;
  id: string;
  line: string;
  reference: string;
  /** El módulo propietario del documento está habilitado. */
  available: boolean;
}

export interface StockMovement {
  id: string;
  occurredAt: string;
  reference: string;
  product: { id: string; name: string };
  warehouse: { id: string; name: string };
  kind: MovementKind;
  /** Decimal como texto; `null` si el movimiento es de la otra dirección. */
  quantityIn: string | null;
  quantityOut: string | null;
  unitAbbreviation: string | null;
  status: MovementStatus;
  source: MovementSource | null;
}

/** Longitud máxima del motivo de una reversión (la misma que valida el servidor). */
export const REVERSAL_REASON_MAX_LENGTH = 200;

/** Si el movimiento se puede revertir desde Inventario; `message` explica la restricción cuando no. */
export interface MovementReversalInfo {
  allowed: boolean;
  code: string | null;
  message: string | null;
}

/** Contramovimiento que revirtió al movimiento. */
export interface MovementReversedBy {
  id: string;
  reference: string;
  occurredAt: string | null;
  reason: string;
  userName: string;
}

export interface StockMovementDetail extends StockMovement {
  quantity: string;
  reason: string;
  user: { id: string | null; name: string };
  reversal: MovementReversalInfo;
  reversedBy: MovementReversedBy | null;
  reversedById: string | null;
  reversesId: string | null;
  createdAt: string;
}

export interface MovementListParams {
  dateFrom?: string;
  dateTo?: string;
  productId?: string;
  warehouseId?: string;
  kind?: MovementKind;
  sourceType?: string;
  /** Documento de origen concreto (con `sourceType`), p. ej. el pedido de una venta. */
  sourceId?: string;
  /** Página base 1. */
  page?: number;
  pageSize?: number;
}

export interface StockMovementDto {
  id: string;
  occurred_at: string;
  reference: string;
  product: { id: string; name: string };
  warehouse: { id: string; name: string };
  kind: MovementKind;
  quantity_in: string | null;
  quantity_out: string | null;
  unit: { abbreviation: string | null };
  status: MovementStatus;
  source: MovementSource | null;
}

export interface StockMovementDetailDto extends StockMovementDto {
  quantity: string;
  reason: string;
  user: { id: string | null; name: string };
  reversed_by: {
    id: string;
    reference?: string;
    occurred_at?: string;
    reason?: string;
    user?: { name: string };
  } | null;
  reverses: { id: string } | null;
  reversal?: MovementReversalInfo;
  created_at: string;
}
