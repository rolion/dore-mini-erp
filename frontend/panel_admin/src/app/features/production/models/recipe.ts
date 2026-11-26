export interface RecipeProduct {
  id: string;
  name: string | null;
  active: boolean;
  unit: { id: string; abbreviation: string } | null;
}

export interface RecipeIngredient {
  productId: string;
  productName: string | null;
  productActive: boolean;
  unitId: string | null;
  unitAbbreviation: string | null;
  /** Cadena decimal con 4 decimales (nunca número). */
  quantity: string;
}

export interface Recipe {
  id: string;
  name: string;
  resultProduct: RecipeProduct;
  yieldQuantity: string;
  ingredients: RecipeIngredient[];
  active: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface RecipeIngredientInput {
  productId: string;
  unitId: string | null;
  quantity: string;
}

export interface RecipeInput {
  name: string;
  resultProductId: string;
  yieldQuantity: string;
  ingredients: RecipeIngredientInput[];
}

export interface RecipeDto {
  id: string;
  name: string;
  result_product: { id: string; name: string | null; active: boolean; unit: { id: string; abbreviation: string } | null };
  yield_quantity: string;
  ingredients: {
    product_id: string;
    product_name: string | null;
    product_active: boolean;
    unit_id: string | null;
    unit_abbreviation: string | null;
    quantity: string;
  }[];
  active: boolean;
  created_at: string;
  updated_at: string;
}

export type RecipeStatus = 'active' | 'inactive' | 'all';

export interface RecipeLineErrors {
  productId?: string;
  unitId?: string;
  quantity?: string;
}

export interface RecipeFieldErrors {
  name?: string;
  resultProductId?: string;
  yieldQuantity?: string;
  ingredients?: string;
  lines: Record<number, RecipeLineErrors>;
}

export class RecipeApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly fields: RecipeFieldErrors = { lines: {} },
    readonly invalidPage = false,
  ) {
    super(message);
  }
}

/** Quita los ceros finales de una cantidad decimal para mostrarla («24.0000» → «24»). */
export function formatQuantity(value: string): string {
  return value.includes('.') ? value.replace(/0+$/, '').replace(/\.$/, '') : value;
}
