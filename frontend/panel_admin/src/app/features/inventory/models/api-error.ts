/** Errores de validación por campo devueltos por el servidor (clave = campo del formulario). */
export type FieldErrors = Partial<Record<string, string[]>>;

export class InventoryApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly fieldErrors: FieldErrors = {},
    /** Código estable de una violación de regla (409): `unit_in_use`, `warehouse_is_default`, ... */
    readonly code: string | null = null,
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

/** Traduce una respuesta HTTP de error a un error con mensaje listo para mostrar. */
export function toApiError(status: number, body: unknown): InventoryApiError {
  if (status === 0) {
    return new InventoryApiError(NETWORK_ERROR_MESSAGE, 0);
  }
  if (status === 400) {
    return new InventoryApiError(VALIDATION_ERROR_MESSAGE, 400, toFieldErrors(body));
  }
  const record = (body && typeof body === 'object' ? body : {}) as { detail?: unknown; code?: unknown };
  const detail = typeof record.detail === 'string' ? record.detail : '';
  const code = typeof record.code === 'string' ? record.code : null;
  if (status === 404) {
    return new InventoryApiError(detail || NOT_FOUND_MESSAGE, 404);
  }
  if (status === 409) {
    return new InventoryApiError(detail || GENERIC_ERROR_MESSAGE, 409, {}, code);
  }
  return new InventoryApiError(GENERIC_ERROR_MESSAGE, status);
}
