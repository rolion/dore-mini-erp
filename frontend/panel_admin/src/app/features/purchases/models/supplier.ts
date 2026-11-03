/** Proveedor. Los campos opcionales ausentes llegan como texto vacío. */
export interface Supplier {
  id: string;
  name: string;
  taxId: string;
  phone: string;
  email: string;
  notes: string;
  active: boolean;
  createdAt: string;
  updatedAt: string;
}

/** Datos editables; el estado solo cambia con activar/desactivar. */
export interface SupplierInput {
  name: string;
  taxId: string;
  phone: string;
  email: string;
  notes: string;
}

/** Forma de respuesta de la API (snake_case). */
export interface SupplierDto {
  id: string;
  name: string;
  tax_id: string;
  phone: string;
  email: string;
  notes: string;
  active: boolean;
  created_at: string;
  updated_at: string;
}

export interface SupplierListParams {
  search?: string;
  active?: boolean;
  /** Página base 1. */
  page?: number;
  pageSize?: number;
}

/** Errores de validación por campo devueltos por el servidor (clave = campo del formulario). */
export type FieldErrors = Partial<Record<keyof SupplierInput, string[]>>;

export class SupplierApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly fieldErrors: FieldErrors = {},
  ) {
    super(message);
    this.name = 'SupplierApiError';
  }
}
