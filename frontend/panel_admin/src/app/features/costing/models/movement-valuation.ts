/** Valoración de movimientos de inventario (módulo Costeo). Cantidades e importes viajan como texto decimal. */

export type CostOrigin = 'purchase_price' | 'manual_adjustment' | 'average_at_exit' | 'reversal_snapshot';
export type ValuationSourceType = 'sales_order' | 'purchase_receipt' | 'inventory_adjustment' | 'inventory_opening';

export const COST_ORIGIN_LABELS: Record<CostOrigin, string> = {
  purchase_price: 'Precio de compra',
  manual_adjustment: 'Valor del ajuste',
  average_at_exit: 'Promedio al salir',
  reversal_snapshot: 'Costo del movimiento original',
};

export const VALUATION_SOURCE_OPTIONS: { value: ValuationSourceType; label: string }[] = [
  { value: 'sales_order', label: 'Pedido de venta' },
  { value: 'purchase_receipt', label: 'Recepción de compra' },
  { value: 'inventory_adjustment', label: 'Ajuste de inventario' },
  { value: 'inventory_opening', label: 'Apertura de existencias' },
];

export interface MovementValuationDto {
  id: number;
  movement_id: string;
  product_id: string;
  product_name: string;
  unit_abbreviation: string | null;
  kind: 'in' | 'out';
  quantity: string;
  unit_cost: string;
  value: string;
  average_before: string;
  average_after: string;
  cost_origin: CostOrigin;
  source_type: ValuationSourceType | null;
  source_id: string;
  source_label: string;
  reverses_movement_id: string | null;
  occurred_at: string;
  status: 'valued';
}

export interface MovementValuation {
  id: number;
  movementId: string;
  productId: string;
  productName: string;
  unitAbbreviation: string | null;
  kind: 'in' | 'out';
  quantity: string;
  unitCost: string;
  value: string;
  averageBefore: string;
  averageAfter: string;
  costOrigin: CostOrigin;
  sourceType: ValuationSourceType | null;
  sourceId: string;
  sourceLabel: string;
  occurredAt: string;
}

export interface MovementValuationParams {
  dateFrom?: string;
  dateTo?: string;
  productId?: string;
  sourceType?: string;
  sourceId?: string;
  movementId?: string;
  page?: number;
  pageSize?: number;
}

export class CostingApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = 'CostingApiError';
  }
}
