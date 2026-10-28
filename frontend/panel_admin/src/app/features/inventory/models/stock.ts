export const OPENING_REFERENCE_MAX_LENGTH = 100;
export const QUANTITY_MAX_DECIMALS = 3;

/** Unidad base de un producto, tal como la necesita el stock (siempre de solo lectura en la apertura). */
export interface StockUnit {
  name: string;
  abbreviation: string;
  allowsFractions: boolean;
}

/** Existencia de un producto en un almacén. `quantity` viaja como texto decimal ("10.000") para no perder precisión. */
export interface StockBalance {
  productId: string;
  productName: string | null;
  warehouseId: string;
  warehouseName: string;
  quantity: string;
  unit: StockUnit | null;
}

export interface StockMovement {
  id: string;
  movementType: string;
  quantity: string;
  movementDate: string;
  reference: string;
  createdAt: string;
}

export const MOVEMENT_TYPE_LABELS: Record<string, string> = {
  opening: 'Apertura',
};

export interface MovementsSummary {
  productId: string;
  productName: string | null;
  warehouseId: string;
  warehouseName: string;
  quantity: string;
  unit: StockUnit | null;
}

export interface MovementsPage {
  count: number;
  results: StockMovement[];
  summary: MovementsSummary;
}

export interface StockListParams {
  warehouseId?: string;
  page?: number;
  pageSize?: number;
}

/** Producto que se puede abrir: activo y con control de stock. */
export interface OpeningProduct {
  id: string;
  name: string;
  unit: StockUnit;
  /** Ya elegido en otra línea (no se permite repetirlo). */
  disabled?: boolean;
}

export interface OpeningLineInput {
  productId: string;
  quantity: string;
}

export interface OpeningInput {
  /** Clave de idempotencia: la misma en cada reintento de una misma confirmación. */
  openingId: string;
  warehouseId: string;
  movementDate: string;
  reference: string;
  lines: OpeningLineInput[];
}

export interface OpeningResult {
  openingId: string;
  warehouseId: string;
  movementDate: string;
  reference: string;
  lines: { productId: string; quantity: string; movementId: string }[];
}

export interface StockUnitDto {
  name: string;
  abbreviation: string;
  allows_fractions: boolean;
}

export interface StockBalanceDto {
  product_id: string;
  product_name: string | null;
  warehouse_id: string;
  warehouse_name: string;
  quantity: string;
  unit: StockUnitDto | null;
}

export interface StockMovementDto {
  id: string;
  movement_type: string;
  quantity: string;
  movement_date: string;
  reference: string;
  created_at: string;
}

export interface MovementsPageDto {
  count: number;
  results: StockMovementDto[];
  summary: {
    product_id: string;
    product_name: string | null;
    warehouse_id: string;
    warehouse_name: string;
    quantity: string;
    unit: StockUnitDto | null;
  };
}

export interface OpeningResultDto {
  opening_id: string;
  warehouse_id: string;
  movement_date: string;
  reference: string;
  lines: { product_id: string; quantity: string; movement_id: string }[];
}

/** Fecha de hoy en formato ISO (yyyy-MM-dd) en la zona horaria local. */
export function todayIso(now: Date = new Date()): string {
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${now.getFullYear()}-${month}-${day}`;
}

/** UUID v4 para la clave de apertura; `crypto.randomUUID` solo existe en contextos seguros, de ahí el respaldo. */
export function newUuid(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (char) => {
    const random = Math.floor(Math.random() * 16);
    return (char === 'x' ? random : (random & 0x3) | 0x8).toString(16);
  });
}

/**
 * Mensaje de error de una cantidad ingresada, o `null` si es válida: número ≥ 0, hasta 3 decimales y entero si la
 * unidad base no admite fracciones. El servidor repite la validación.
 */
export function quantityError(raw: string, allowsFractions: boolean): string | null {
  const text = raw.trim();
  if (text === '') {
    return 'La cantidad es obligatoria.';
  }
  if (!/^\d+(\.\d+)?$/.test(text)) {
    return 'Ingresa un número mayor o igual a cero.';
  }
  const decimals = text.split('.')[1] ?? '';
  if (decimals.length > QUANTITY_MAX_DECIMALS) {
    return `La cantidad admite como máximo ${QUANTITY_MAX_DECIMALS} decimales.`;
  }
  if (!allowsFractions && /[1-9]/.test(decimals)) {
    return 'La unidad base de este producto no admite fracciones.';
  }
  return null;
}

/** "10.000" → "10"; "2.500" → "2.5" (para mostrar sin ceros sobrantes). */
export function formatQuantity(quantity: string): string {
  return quantity.includes('.') ? quantity.replace(/\.?0+$/, '') : quantity;
}
