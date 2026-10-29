/** Producto del catálogo. `salePrice` viaja como texto decimal ("35.00") para no perder precisión. */
export interface BaseUnit {
  id: string;
  name: string;
  abbreviation: string;
  /** Si la unidad admite cantidades fraccionarias; ausente cuando el dato no se conoce. */
  allowsFractions?: boolean;
}

/** Unidad base tal como la devuelve la API (snake_case). */
export interface BaseUnitDto {
  id: string;
  name: string;
  abbreviation: string;
  allows_fractions?: boolean;
}

export interface Product {
  id: string;
  name: string;
  description: string;
  salePrice: string;
  active: boolean;
  /** Controla existencias; sin Inventario habilitado la API lo devuelve igual, la UI lo oculta. */
  tracksStock: boolean;
  baseUnit: BaseUnit | null;
  createdAt: string;
  updatedAt: string;
}

/** Datos comerciales editables; el estado solo cambia con activar/desactivar. */
export interface ProductInput {
  name: string;
  description: string;
  salePrice: string;
  /** Solo se envían con Inventario habilitado. */
  tracksStock?: boolean;
  baseUnitId?: string | null;
}

/** Forma de respuesta de la API (snake_case). */
export interface ProductDto {
  id: string;
  name: string;
  description: string;
  sale_price: string;
  active: boolean;
  tracks_stock: boolean;
  base_unit: BaseUnitDto | null;
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
    /** Código estable de una violación de regla (409): `stock_history_locked`. */
    readonly code: string | null = null,
  ) {
    super(message);
    this.name = 'ProductApiError';
  }
}
