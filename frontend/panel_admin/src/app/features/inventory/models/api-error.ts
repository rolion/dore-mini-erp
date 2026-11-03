/** Errores de validación por campo devueltos por el servidor (clave = campo del formulario). */
export type FieldErrors = Partial<Record<string, string[]>>;

/** Datos de un 409 `insufficient_stock`: qué se pidió y cuánto hay (cantidades como texto decimal). */
export interface InsufficientStockInfo {
  productName: string;
  warehouseName: string;
  requested: string;
  available: string;
  unit: string;
}

export class InventoryApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly fieldErrors: FieldErrors = {},
    /** Código estable de una violación de regla (409): `unit_in_use`, `warehouse_is_default`, ... */
    readonly code: string | null = null,
    /** Errores por línea de una apertura (misma posición que las líneas enviadas). */
    readonly lineErrors: FieldErrors[] = [],
    /** Productos de una apertura que ya tienen movimientos en el almacén (409 `stock_history_exists`). */
    readonly historyProductIds: string[] = [],
    /** Saldo vigente de un ajuste cuyo saldo cambió desde el conteo (409 `balance_changed`). */
    readonly currentBalance: string | null = null,
    /** Detalle de una salida rechazada por saldo insuficiente (409 `insufficient_stock`). */
    readonly insufficientStock: InsufficientStockInfo | null = null,
  ) {
    super(message);
    this.name = 'InventoryApiError';
  }
}

export const NETWORK_ERROR_MESSAGE = 'No se pudo conectar con el servidor. Inténtalo de nuevo.';
export const GENERIC_ERROR_MESSAGE = 'Ocurrió un error inesperado. Inténtalo de nuevo.';
export const VALIDATION_ERROR_MESSAGE = 'Revisa los datos ingresados.';
export const NOT_FOUND_MESSAGE = 'No se encontró el registro.';

/** Campo del servidor → campo del formulario. */
const FIELD_MAP: Record<string, string> = {
  name: 'name',
  abbreviation: 'abbreviation',
  allows_fractions: 'allowsFractions',
  description: 'description',
  is_default: 'isDefault',
  warehouse_id: 'warehouseId',
  movement_date: 'movementDate',
  reference: 'reference',
  product_id: 'productId',
  quantity: 'quantity',
  counted_quantity: 'countedQuantity',
  expected_system_quantity: 'expectedSystemQuantity',
  reason: 'reason',
  total_value: 'totalValue',
  non_field_errors: 'nonFieldErrors',
};

function toFieldErrors(body: unknown): FieldErrors {
  const errors: FieldErrors = {};
  if (body && typeof body === 'object') {
    for (const [serverField, value] of Object.entries(body as Record<string, unknown>)) {
      const field = FIELD_MAP[serverField];
      if (field && Array.isArray(value)) {
        errors[field] = value.map(String);
      }
    }
  }
  return errors;
}

/** `lines` de un 400: una lista con un objeto de errores por línea (o un error general de la lista). */
function toLineErrors(body: unknown): FieldErrors[] {
  const lines = body && typeof body === 'object' ? (body as Record<string, unknown>)['lines'] : undefined;
  return Array.isArray(lines) ? lines.map((line) => toFieldErrors(line)) : [];
}

function toHistoryProductIds(body: unknown): string[] {
  const lines = body && typeof body === 'object' ? (body as Record<string, unknown>)['lines'] : undefined;
  if (!Array.isArray(lines)) {
    return [];
  }
  return lines
    .map((line) => (line && typeof line === 'object' ? (line as Record<string, unknown>)['product_id'] : null))
    .filter((id): id is string => typeof id === 'string');
}

function toInsufficientStock(body: unknown): InsufficientStockInfo | null {
  const record = (body && typeof body === 'object' ? body : {}) as {
    product?: { name?: unknown };
    warehouse?: { name?: unknown };
    unit?: { abbreviation?: unknown } | null;
    requested?: unknown;
    available?: unknown;
  };
  if (typeof record.requested !== 'string' || typeof record.available !== 'string') {
    return null;
  }
  const text = (value: unknown): string => (typeof value === 'string' ? value : '');
  return {
    productName: text(record.product?.name),
    warehouseName: text(record.warehouse?.name),
    requested: record.requested,
    available: record.available,
    unit: text(record.unit?.abbreviation),
  };
}

/** Traduce una respuesta HTTP de error a un error con mensaje listo para mostrar. */
export function toApiError(status: number, body: unknown): InventoryApiError {
  if (status === 0) {
    return new InventoryApiError(NETWORK_ERROR_MESSAGE, 0);
  }
  if (status === 400) {
    return new InventoryApiError(VALIDATION_ERROR_MESSAGE, 400, toFieldErrors(body), null, toLineErrors(body));
  }
  const record = (body && typeof body === 'object' ? body : {}) as { detail?: unknown; code?: unknown };
  const detail = typeof record.detail === 'string' ? record.detail : '';
  const code = typeof record.code === 'string' ? record.code : null;
  if (status === 404) {
    return new InventoryApiError(detail || NOT_FOUND_MESSAGE, 404);
  }
  if (status === 409) {
    const history = code === 'stock_history_exists' ? toHistoryProductIds(body) : [];
    const balance = (body as { current_balance?: unknown } | null)?.current_balance;
    const current = code === 'balance_changed' && typeof balance === 'string' ? balance : null;
    const stock = code === 'insufficient_stock' ? toInsufficientStock(body) : null;
    return new InventoryApiError(detail || GENERIC_ERROR_MESSAGE, 409, {}, code, [], history, current, stock);
  }
  return new InventoryApiError(GENERIC_ERROR_MESSAGE, status);
}
