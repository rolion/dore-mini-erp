export type MovementKind = 'in' | 'out';
export type MovementStatus = 'confirmed' | 'reversed';

export const MOVEMENT_KIND_LABELS: Record<MovementKind, string> = { in: 'Entrada', out: 'Salida' };
export const MOVEMENT_STATUS_LABELS: Record<MovementStatus, string> = {
  confirmed: 'Confirmado',
  reversed: 'Revertido',
};

/** Clases de documento de origen que conoce el servidor, con la etiqueta del filtro. */
export const SOURCE_TYPE_OPTIONS: readonly { value: string; label: string }[] = [
  { value: 'sales_order', label: 'Pedido de venta' },
  { value: 'purchase_receipt', label: 'Recepción de compra' },
  { value: 'inventory_adjustment', label: 'Ajuste de inventario' },
  { value: 'none', label: 'Sin documento' },
];

/** Pantalla de destino por clase de origen; solo existen las de módulos ya construidos. */
export const SOURCE_ROUTES: Readonly<Record<string, (id: string) => string[]>> = {
  sales_order: (id) => ['/pocketbiz/sales/orders', id],
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

export interface StockMovementDetail extends StockMovement {
  quantity: string;
  reason: string;
  user: { id: string | null; name: string };
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
  reversed_by: { id: string } | null;
  reverses: { id: string } | null;
  created_at: string;
}
