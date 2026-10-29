import { MovementKind, MovementStatus } from './movement';

export const ADJUSTMENT_REASON_MAX_LENGTH = 200;

export interface StockAdjustment {
  id: string;
  reference: string;
  createdAt: string;
  product: { id: string; name: string };
  warehouse: { id: string; name: string };
  /** Decimales como texto: saldo del sistema al confirmar, cantidad contada y diferencia con signo. */
  systemQuantity: string;
  countedQuantity: string;
  difference: string;
  kind: MovementKind;
  unitAbbreviation: string | null;
  user: { id: string | null; name: string };
  status: MovementStatus;
}

export interface StockAdjustmentDetail extends StockAdjustment {
  reason: string;
  movementId: string;
}

export interface AdjustmentListParams {
  dateFrom?: string;
  dateTo?: string;
  productId?: string;
  warehouseId?: string;
  /** Página base 1. */
  page?: number;
  pageSize?: number;
}

export interface AdjustmentInput {
  /** Clave de idempotencia: la misma en cada reintento de una misma confirmación. */
  adjustmentId: string;
  productId: string;
  warehouseId: string;
  countedQuantity: string;
  /** Saldo que la persona vio al contar; el servidor lo compara con el vigente. */
  expectedSystemQuantity: string;
  reason: string;
}

export interface AdjustmentBalance {
  systemQuantity: string;
  unit: { abbreviation: string; allowsFractions: boolean } | null;
}

export interface StockAdjustmentDto {
  id: string;
  reference: string;
  created_at: string;
  product: { id: string; name: string };
  warehouse: { id: string; name: string };
  system_quantity: string;
  counted_quantity: string;
  difference: string;
  kind: MovementKind;
  unit: { abbreviation: string | null };
  user: { id: string | null; name: string };
  status: MovementStatus;
}

export interface StockAdjustmentDetailDto extends StockAdjustmentDto {
  reason: string;
  movement: { id: string };
}

export interface AdjustmentBalanceDto {
  system_quantity: string;
  unit: { abbreviation: string; allows_fractions: boolean } | null;
}

const SCALE = 10000;

function scaled(value: string): number {
  return Math.round(Number(value) * SCALE);
}

/** Diferencia contada − saldo como texto con signo, sin ceros sobrantes ("-3", "2.5", "0"); solo para mostrar. */
export function differenceOf(counted: string, balance: string): string {
  const diff = scaled(counted) - scaled(balance);
  const text = (Math.abs(diff) / SCALE).toFixed(4).replace(/\.?0+$/, '');
  return diff < 0 ? `-${text}` : text;
}

/** Sentido del ajuste según el signo de la diferencia; `null` si no hay diferencia. */
export function directionOf(difference: string): MovementKind | null {
  const value = Number(difference);
  if (value === 0 || Number.isNaN(value)) {
    return null;
  }
  return value > 0 ? 'in' : 'out';
}

/** Diferencia para mostrar con "+" en las entradas: "+2.5", "-3". */
export function signedDifference(difference: string): string {
  const text = difference.includes('.') ? difference.replace(/\.?0+$/, '') : difference;
  return Number(text) > 0 ? `+${text}` : text;
}
