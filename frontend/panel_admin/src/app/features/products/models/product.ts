/** Producto del catálogo. `salePrice` viaja como texto decimal ("35.00") para no perder precisión. */
export interface Product {
  id: string;
  name: string;
  description: string;
  salePrice: string;
  active: boolean;
  createdAt: string;
  updatedAt: string;
}

/** Datos comerciales editables; el estado solo cambia con activar/desactivar. */
export interface ProductInput {
  name: string;
  description: string;
  salePrice: string;
}

/** Forma de respuesta de la API (snake_case). */
export interface ProductDto {
  id: string;
  name: string;
  description: string;
  sale_price: string;
  active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProductListParams {
  search?: string;
  active?: boolean;
  /** Página base 1. */
  page?: number;
  pageSize?: number;
}

/** Errores de validación por campo devueltos por el servidor (clave = campo del formulario). */
export type FieldErrors = Partial<Record<keyof ProductInput, string[]>>;

export class ProductApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly fieldErrors: FieldErrors = {},
  ) {
    super(message);
    this.name = 'ProductApiError';
  }
}
