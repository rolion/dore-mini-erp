/** Cliente. Los campos opcionales ausentes llegan como texto vacío. */
export interface Customer {
  id: string;
  name: string;
  phone: string;
  email: string;
  notes: string;
  active: boolean;
  createdAt: string;
  updatedAt: string;
}

/** Datos de contacto y notas editables; el estado solo cambia con activar/desactivar. */
export interface CustomerInput {
  name: string;
  phone: string;
  email: string;
  notes: string;
}

/** Forma de respuesta de la API (snake_case). */
export interface CustomerDto {
  id: string;
  name: string;
  phone: string;
  email: string;
  notes: string;
  active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Page<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface CustomerListParams {
  search?: string;
  active?: boolean;
  /** Página base 1. */
  page?: number;
  pageSize?: number;
}

/** Resumen de un pedido del cliente; lo proveerá Sales (`GET /api/orders/?customer_id=`). */
export interface CustomerOrderSummary {
  id: string;
  date: string;
  /** Texto decimal ("120.50"); no se opera con aritmética de coma flotante. */
  total: string;
  status: string;
}

/** Otro cliente con el mismo teléfono, devuelto al intentar crear un duplicado. */
export interface DuplicateMatch {
  id: string;
  name: string;
  phone: string;
  active: boolean;
}

/** Errores de validación por campo devueltos por el servidor (clave = campo del formulario). */
export type FieldErrors = Partial<Record<keyof CustomerInput, string[]>>;

export class CustomerApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly fieldErrors: FieldErrors = {},
  ) {
    super(message);
    this.name = 'CustomerApiError';
  }
}

/** El teléfono ya existe: el alta solo prosigue si el usuario lo confirma. */
export class DuplicateCustomerError extends CustomerApiError {
  constructor(
    message: string,
    readonly matches: DuplicateMatch[],
  ) {
    super(message, 409);
    this.name = 'DuplicateCustomerError';
  }
}
