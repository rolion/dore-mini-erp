import { ProductCategory } from '../../products/models/product';

export const OPENING_REFERENCE_MAX_LENGTH = 100;
export const QUANTITY_MAX_DECIMALS = 3;

/** Unidad base de un producto, tal como la necesita el stock (siempre de solo lectura en la apertura). */
export interface StockUnit {
  abbreviation: string;
  allowsFractions: boolean;
}

/** Existencia de un producto en un almacén. `quantity` viaja como texto decimal ("10.000") para no perder precisión. */
export interface StockBalance {
  productId: string;
  productName: string;
  productActive: boolean;
  warehouseId: string;
  warehouseName: string;
  warehouseActive: boolean;
  /** Clasificación del producto en Catálogo; `null` si aún no se clasifica. */
  category: ProductCategory | null;
  canBuy: boolean;
  canSell: boolean;
  quantity: string;
  /** Derivado por el servidor del signo del saldo. */
  balanceState: BalanceState;
  unit: StockUnit | null;
}

/** Existencia de un producto en un almacén, con lo necesario para decidir las acciones del detalle. */
export interface StockPosition extends StockBalance {
  hasHistory: boolean;
  canRegisterOpening: boolean;
  canRegisterAdjustment: boolean;
}

export type BalanceState = 'zero' | 'positive' | 'negative';
export type BalanceFilter = '' | 'zero' | 'nonzero' | 'negative';
export type ActiveFilter = 'true' | 'false' | 'all';
/** Categoría del producto o `none` (sin clasificar); vacío = todas. */
export type CategoryFilter = '' | ProductCategory | 'none';
/** Filtro de un uso (comprable/vendible): vacío = todos. */
export type UseFilter = '' | 'true' | 'false';

export const CATEGORY_FILTER_OPTIONS: readonly { value: CategoryFilter; label: string }[] = [
  { value: '', label: 'Todas las clasificaciones' },
  { value: 'raw_material', label: 'Materia prima' },
  { value: 'packaging', label: 'Empaque' },
  { value: 'intermediate', label: 'Intermedio' },
  { value: 'finished', label: 'Terminado' },
  { value: 'merchandise', label: 'Mercadería' },
  { value: 'none', label: 'Sin clasificar' },
];

export const USE_FILTER_OPTIONS: readonly { value: UseFilter; label: string }[] = [
  { value: '', label: 'Todos' },
  { value: 'true', label: 'Sí' },
  { value: 'false', label: 'No' },
];

export const BALANCE_FILTER_OPTIONS: readonly { value: BalanceFilter; label: string }[] = [
  { value: '', label: 'Todos los saldos' },
  { value: 'zero', label: 'Con saldo cero' },
  { value: 'nonzero', label: 'Con saldo distinto de cero' },
  { value: 'negative', label: 'Con saldo negativo' },
];

export const ACTIVE_FILTER_OPTIONS: readonly { value: ActiveFilter; label: string }[] = [
  { value: 'true', label: 'Activos' },
  { value: 'false', label: 'Inactivos' },
  { value: 'all', label: 'Todos' },
];

export interface StockListParams {
  search?: string;
  active?: ActiveFilter;
  balance?: BalanceFilter;
  category?: CategoryFilter;
  canBuy?: UseFilter;
  canSell?: UseFilter;
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
  /** `movementId` es nulo en las líneas con cantidad 0: no generan movimiento. */
  lines: { productId: string; quantity: string; movementId: string | null }[];
}

export interface StockUnitDto {
  abbreviation: string;
  allows_fractions: boolean;
}

export interface StockBalanceDto {
  product_id: string;
  product_name: string;
  product_active: boolean;
  warehouse_id: string;
  warehouse_name: string;
  warehouse_active: boolean;
  category: ProductCategory | null;
  can_buy: boolean;
  can_sell: boolean;
  quantity: string;
  balance_state: BalanceState;
  unit: StockUnitDto | null;
}

export interface StockPositionDto extends StockBalanceDto {
  has_history: boolean;
  can_register_opening: boolean;
  can_register_adjustment: boolean;
}

export interface OpeningResultDto {
  opening_id: string;
  warehouse_id: string;
  movement_date: string;
  reference: string;
  lines: { product_id: string; quantity: string; movement_id: string | null }[];
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
