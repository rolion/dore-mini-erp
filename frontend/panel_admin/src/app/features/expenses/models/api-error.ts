import { tr } from '../../../core/i18n/translate';
/** Errores de validación por campo devueltos por el servidor (clave = campo del formulario). */
export type FieldErrors = Partial<Record<string, string[]>>;

export class ExpensesApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly fieldErrors: FieldErrors = {},
    /** Código estable de una violación de regla (409): `already_voided`, `expense_voided`. */
    readonly code: string | null = null,
  ) {
    super(message);
    this.name = 'ExpensesApiError';
  }
}

export const NETWORK_ERROR_MESSAGE = (): string => tr('CUSTOMERS.CUSTOMERS_API_SERVICE.NO_SE_PUDO_CONECTAR_CON');
export const GENERIC_ERROR_MESSAGE = (): string => tr('CUSTOMERS.CUSTOMERS_API_SERVICE.OCURRIO_UN_ERROR_INESPERADO_INTENTALO');
export const VALIDATION_ERROR_MESSAGE = (): string => tr('CUSTOMERS.CUSTOMERS_API_SERVICE.REVISA_LOS_DATOS_INGRESADOS');
export const NOT_FOUND_MESSAGE = (): string => tr('EXPENSES.API_ERROR.NO_SE_ENCONTRO_EL_REGISTRO');

/** Campo del servidor → campo del formulario. */
const FIELD_MAP: Record<string, string> = {
  description: 'description',
  amount: 'amount',
  category_id: 'categoryId',
  expense_date: 'expenseDate',
  payment_method: 'paymentMethod',
  supplier_name: 'supplierName',
  notes: 'notes',
  name: 'name',
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

function detailOf(body: unknown): { detail: string; code: string | null } {
  const record = (body && typeof body === 'object' ? body : {}) as { detail?: unknown; code?: unknown };
  return {
    detail: typeof record.detail === 'string' ? record.detail : '',
    code: typeof record.code === 'string' ? record.code : null,
  };
}

/** Traduce una respuesta HTTP de error a un error con mensaje listo para mostrar. */
export function toApiError(status: number, body: unknown): ExpensesApiError {
  if (status === 0) {
    return new ExpensesApiError(NETWORK_ERROR_MESSAGE(), 0);
  }
  if (status === 400) {
    return new ExpensesApiError(VALIDATION_ERROR_MESSAGE(), 400, toFieldErrors(body));
  }
  const { detail, code } = detailOf(body);
  if (status === 404) {
    return new ExpensesApiError(detail || NOT_FOUND_MESSAGE(), 404);
  }
  if (status === 409) {
    return new ExpensesApiError(detail || GENERIC_ERROR_MESSAGE(), 409, {}, code);
  }
  return new ExpensesApiError(GENERIC_ERROR_MESSAGE(), status);
}
