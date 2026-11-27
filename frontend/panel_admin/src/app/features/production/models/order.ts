import { formatQuantity } from './recipe';

export type OrderStatus = 'draft' | 'in_preparation' | 'refrigerating' | 'ready_to_pack';
export type OrderStatusFilter = 'all' | OrderStatus;

/** Tope de preparaciones que acepta el servidor (EDGE-02). */
export const MAX_PREPARATIONS = 99999;

/** Tope de packs por empaque que acepta el servidor. */
export const MAX_PACKS = 99999;

export interface ProductionOrderIngredient {
  productId: string;
  productName: string | null;
  unitId: string | null;
  unitAbbreviation: string | null;
  /** Cadena decimal con 4 decimales (nunca número). */
  quantityPerPreparation: string;
  expectedQuantity: string;
  /** Consumo real; solo existe tras pasar a refrigeración. */
  actualQuantity: string | null;
}

export interface OrderRelease {
  minHours: number;
  /** ISO 8601: primera hora habilitada para liberar el lote. */
  releasableFrom: string | null;
  /** Lo decide el servidor al consultar; la acción lo vuelve a validar. */
  canRelease: boolean;
}

export interface PackingEntry {
  id: string;
  number: number;
  packs: number;
  packProduct: { id: string; name: string };
  bagProduct: { id: string; name: string };
  /** Etiqueta opcional; `null` si no se usó. */
  labelProduct: { id: string; name: string } | null;
  /** Cadenas decimales con 4 decimales. */
  bulkQuantity: string;
  bagsQuantity: string;
  /** Cantidad de bolsa usada por pack en esa tanda. */
  bagPerPack: string;
  labelsQuantity: string;
  lot: { id: string; code: string };
  /** Costo total (2 decimales) y unitario (6); `null` = sin costo. */
  costTotal: string | null;
  unitCost: string | null;
  createdAt: string;
  createdBy: string | null;
}

/** Empaque en packs de 6: saldo a granel e historial (solo en órdenes listas para empacar). */
export interface OrderPacking {
  unitsPerPack: number;
  /** Largo/cantidad de bolsa sugerido por pack (en la unidad de la bolsa), texto decimal. */
  suggestedBagPerPack: string;
  labelsPerPack: number;
  bulkAvailable: string;
  bulkUnitAbbreviation: string | null;
  packings: PackingEntry[];
}

export interface PackInput {
  /** UUID por intento: reintentar el mismo no duplica el empaque. */
  requestId: string;
  packs: number;
  packProductId: string;
  bagProductId: string;
  /** Cantidad de bolsa por pack, en la unidad del producto bolsa (p. ej. 0.17 m). */
  bagPerPack: number;
  /** Etiqueta opcional (una por pack); `null` = sin etiqueta. */
  labelProductId: string | null;
}

export interface ProductionOrder {
  id: string;
  number: number;
  status: OrderStatus;
  recipe: { id: string; name: string };
  resultProduct: { id: string; name: string | null; unit: { id: string; abbreviation: string } | null };
  warehouse: { id: string; name: string };
  preparations: number;
  yieldPerPreparation: string;
  expectedOutput: string;
  ingredients: ProductionOrderIngredient[];
  createdAt: string;
  startedAt: string | null;
  actualOutput: string | null;
  enteredAt: string | null;
  lot: { id: string; code: string } | null;
  /** Costo total consumido con 2 decimales; `null` = sin costo. */
  costTotal: string | null;
  release: OrderRelease | null;
  releasedAt: string | null;
  releasedBy: string | null;
  packing: OrderPacking | null;
}

export interface ProductionOrderDto {
  id: string;
  number: number;
  status: OrderStatus;
  recipe: { id: string; name: string };
  result_product: { id: string; name: string | null; unit: { id: string; abbreviation: string } | null };
  warehouse: { id: string; name: string };
  preparations: number;
  yield_per_preparation: string;
  expected_output: string;
  ingredients: {
    product_id: string;
    product_name: string | null;
    unit_id: string | null;
    unit_abbreviation: string | null;
    quantity_per_preparation: string;
    expected_quantity: string;
    actual_quantity: string | null;
  }[];
  created_at: string;
  started_at: string | null;
  actual_output: string | null;
  entered_at: string | null;
  lot: { id: string; code: string } | null;
  cost_total: string | null;
  release: { min_hours: number; releasable_from: string | null; can_release: boolean } | null;
  released_at: string | null;
  released_by: string | null;
  packing: {
    units_per_pack: number;
    suggested_bag_per_pack: string;
    labels_per_pack: number;
    bulk_available: string;
    bulk_unit_abbreviation: string | null;
    packings: {
      id: string; number: number; packs: number;
      pack_product: { id: string; name: string }; bag_product: { id: string; name: string };
      label_product: { id: string; name: string } | null;
      bulk_quantity: string; bags_quantity: string; bag_per_pack: string; labels_quantity: string; lot: { id: string; code: string };
      cost_total: string | null; unit_cost: string | null; created_at: string; created_by: string | null;
    }[];
  } | null;
}

export interface OrderWarehouse {
  id: string;
  name: string;
  isDefault: boolean;
}

export interface OrderWarehouseDto {
  id: string;
  name: string;
  is_default: boolean;
}

export interface OrderCreateInput {
  recipeId: string;
  warehouseId: string;
  preparations: number;
}

export interface OrderUpdateInput {
  warehouseId: string;
  preparations: number;
}

export interface RefrigerateInput {
  /** ISO 8601 con zona horaria. */
  enteredAt: string;
  actualOutput: string;
  ingredients: { productId: string; actualQuantity: string }[];
}

export interface OrderShortage {
  productId: string;
  productName: string;
  unitAbbreviation: string | null;
  requested: string;
  available: string;
  missing: string;
}

export interface OrderFieldErrors {
  actualOutput?: string;
  enteredAt?: string;
  ingredients?: string;
  /** Error por línea de `ingredients` (mismo orden que las filas de la orden; `undefined` = sin error). */
  ingredientLines?: (string | undefined)[];
  /** Primera hora habilitada que devuelve el 409 `release_too_early`. */
  releasableFrom?: string;
  /** Código del 409 (`insufficient_stock`, `fiscal_period_missing`…). */
  code?: string;
  recipeId?: string;
  warehouseId?: string;
  preparations?: string;
  detail?: string;
  packs?: string;
  packProductId?: string;
  bagProductId?: string;
  bagPerPack?: string;
  labelProductId?: string;
  requestId?: string;
}

export class OrderApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly fields: OrderFieldErrors = {},
    readonly invalidPage = false,
    readonly shortages: OrderShortage[] = [],
  ) {
    super(message);
  }
}

/** Número de orden mostrado como «OP-0001» (4 dígitos como mínimo). */
export function formatOrderNumber(value: number): string {
  return `OP-${String(value).padStart(4, '0')}`;
}

const SCALE = 4;
const DECIMAL = /^\d+(\.\d{1,4})?$/;

/** Cantidad decimal → entero escalado a 4 decimales (sin pasar por `float`); `null` si no es válida. */
export function toScaled(value: string): bigint | null {
  const text = value.trim();
  if (!DECIMAL.test(text)) return null;
  const [whole, fraction = ''] = text.split('.');
  return BigInt(whole + fraction.padEnd(SCALE, '0'));
}

/** Entero escalado → cadena sin ceros sobrantes («120», «7.5»). */
export function fromScaled(value: bigint): string {
  const digits = value.toString().padStart(SCALE + 1, '0');
  return formatQuantity(`${digits.slice(0, -SCALE)}.${digits.slice(-SCALE)}`);
}

/** Cantidad × preparaciones con aritmética entera; `null` si algún dato no es válido. */
export function multiplyQuantity(quantity: string, preparations: number): string | null {
  const scaled = toScaled(quantity);
  if (scaled === null || !Number.isInteger(preparations)) return null;
  return fromScaled(scaled * BigInt(preparations));
}

/** Preparaciones válidas: entero de 1 a 99999 escrito solo con dígitos. */
export function parsePreparations(value: string): number | null {
  const text = value.trim();
  if (!/^\d+$/.test(text)) return null;
  const parsed = Number(text);
  return parsed >= 1 && parsed <= MAX_PREPARATIONS ? parsed : null;
}
