import { ParamMap } from '@angular/router';

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * Detalle de existencia al que volver tras una apertura o un ajuste, o `null` si la navegación no viene de uno.
 * Solo se acepta el valor cerrado `return=stock` con ambos ids válidos: nunca una URL libre.
 */
export function stockReturnLink(query: ParamMap): string[] | null {
  const productId = query.get('product_id');
  const warehouseId = query.get('warehouse_id');
  if (query.get('return') !== 'stock' || !productId || !warehouseId) {
    return null;
  }
  if (!UUID_PATTERN.test(productId) || !UUID_PATTERN.test(warehouseId)) {
    return null;
  }
  return ['/pocketbiz/inventory/stock', productId, warehouseId];
}
