/** Uso que se muestra de un producto: se vende, se compra o sirve de insumo para producir otros productos. */
export type ProductUseKind = 'sell' | 'buy' | 'ingredient';

/** Categorías cuyos productos se pueden usar para producir otros (clasificación visual, no una regla). */
const INGREDIENT_CATEGORIES: readonly string[] = ['raw_material', 'packaging', 'intermediate'];

export interface ProductUsesInput {
  canSell: boolean;
  canBuy: boolean;
  /** `null` o vacío en productos por revisar. */
  category: string | null;
}

/** Usos a mostrar, en orden fijo: vendible, comprable, insumo. La categoría no limita lo que se puede hacer. */
export function productUses(product: ProductUsesInput): ProductUseKind[] {
  const uses: ProductUseKind[] = [];
  if (product.canSell) {
    uses.push('sell');
  }
  if (product.canBuy) {
    uses.push('buy');
  }
  if (product.category && INGREDIENT_CATEGORIES.includes(product.category)) {
    uses.push('ingredient');
  }
  return uses;
}
