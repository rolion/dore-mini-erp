/** Producto del catálogo. `salePrice` viaja como texto decimal ("35.00") para no perder precisión. */
export interface BaseUnit {
  id: string;
  name: string;
  abbreviation: string;
}

/** Categoría operativa: organiza y filtra, no limita los usos del producto. */
export type ProductCategory = 'raw_material' | 'packaging' | 'intermediate' | 'finished' | 'merchandise';

export const PRODUCT_CATEGORIES: readonly { value: ProductCategory; label: string }[] = [
  { value: 'raw_material', label: 'Materia prima' },
  { value: 'packaging', label: 'Empaque' },
  { value: 'intermediate', label: 'Intermedio' },
  { value: 'finished', label: 'Terminado' },
  { value: 'merchandise', label: 'Mercadería' },
];

export function categoryLabel(category: ProductCategory | null): string {
  return PRODUCT_CATEGORIES.find((c) => c.value === category)?.label ?? 'Sin clasificar';
}

export interface Product {
  id: string;
  name: string;
  description: string;
  /** `null` cuando el producto no se vende. */
  salePrice: string | null;
  /** `null` en productos migrados que aún no se clasifican (por revisar). */
  category: ProductCategory | null;
  canBuy: boolean;
  canSell: boolean;
  needsReview: boolean;
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
  /** Obligatorio solo si `canSell`; sin precio se envía `null`. */
  salePrice: string | null;
  category: ProductCategory;
  canBuy: boolean;
  canSell: boolean;
  /** Solo se envían con Inventario habilitado. */
  tracksStock?: boolean;
  baseUnitId?: string | null;
}

/** Forma de respuesta de la API (snake_case). */
export interface ProductDto {
  id: string;
  name: string;
  description: string;
  sale_price: string | null;
  category: ProductCategory | null;
  can_buy: boolean;
  can_sell: boolean;
  needs_review: boolean;
  active: boolean;
  tracks_stock: boolean;
  base_unit: BaseUnit | null;
  created_at: string;
  updated_at: string;
}

export interface ProductListParams {
  search?: string;
  active?: boolean;
  canBuy?: boolean;
  canSell?: boolean;
  /** Una categoría, o `unclassified` para los productos por revisar. */
  category?: ProductCategory | 'unclassified';
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
