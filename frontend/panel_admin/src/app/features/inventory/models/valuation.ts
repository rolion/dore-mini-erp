/** Valoración inicial del inventario (módulo Costeo). Cantidades e importes viajan como texto decimal. */

export type ValuationStatus = 'not_adopted' | 'adopted';

export interface ProposalWarehouse {
  warehouseId: string;
  warehouseName: string;
  quantity: string;
}

export interface ProposalLine {
  productId: string;
  productName: string;
  unitAbbreviation: string | null;
  reconciledQuantity: string;
  warehouses: ProposalWarehouse[];
}

export interface ProposalBlocker {
  productId: string;
  productName: string;
  warehouseId: string;
  warehouseName: string;
  quantity: string;
}

export interface Proposal {
  lines: ProposalLine[];
  blockers: ProposalBlocker[];
}

export interface ValuationLine {
  productId: string;
  productName: string;
  unitAbbreviation: string | null;
  reconciledQuantity: string;
  totalValue: string;
  unitCost: string;
  declaredZero: boolean;
  source: string;
}

export interface Adoption {
  id: string;
  cutoffAt: string;
  method: string;
  userName: string;
  lines: ValuationLine[];
}

export interface Valuation {
  status: ValuationStatus;
  adoption: Adoption | null;
}

export interface AdoptionLineInput {
  productId: string;
  reconciledQuantity: string;
  totalValue: string;
  declaredZero: boolean;
  source: string;
}

export interface AdoptionInput {
  adoptionId: string;
  lines: AdoptionLineInput[];
}

export interface ProposalLineDto {
  product_id: string;
  product_name: string;
  unit_abbreviation: string | null;
  reconciled_quantity: string;
  warehouses: { warehouse_id: string; warehouse_name: string; quantity: string }[];
}

export interface ProposalBlockerDto {
  product_id: string;
  product_name: string;
  warehouse_id: string;
  warehouse_name: string;
  quantity: string;
}

export interface ProposalDto {
  lines: ProposalLineDto[];
  blockers: ProposalBlockerDto[];
}

export interface ValuationLineDto {
  product_id: string;
  product_name: string;
  unit_abbreviation: string | null;
  reconciled_quantity: string;
  total_value: string;
  unit_cost: string;
  declared_zero: boolean;
  source: string;
}

export interface ValuationDto {
  status: ValuationStatus;
  adoption: {
    id: string;
    cutoff_at: string;
    method: string;
    user_name: string;
    lines: ValuationLineDto[];
  } | null;
}

/** Estado de captura de una línea: «Pendiente» (sin valor), inválida, o lista. */
export type LineValueState = 'pending' | 'invalid' | 'zero-undeclared' | 'ok';

export const PENDING_LABEL = 'Pendiente';
export const DEFAULT_SOURCE = 'Ingreso manual';
export const SOURCE_MAX_LENGTH = 200;
export const METHOD_LABEL = 'Promedio ponderado móvil (costo de gestión)';

const MONEY_PATTERN = /^\d+(\.\d{1,2})?$/;
const QUANTITY_PATTERN = /^\d+(\.\d{1,4})?$/;
const MAX_TOTAL_DIGITS = 14;

/** Estado de una línea según lo escrito (la regla vigente es la del servidor; esto solo guía la captura). */
export function lineValueState(totalValue: string, declaredZero: boolean): LineValueState {
  const text = totalValue.trim();
  if (declaredZero) {
    return text === '' || (MONEY_PATTERN.test(text) && Number(text) === 0) ? 'ok' : 'invalid';
  }
  if (text === '') {
    return 'pending';
  }
  if (!MONEY_PATTERN.test(text) || text.split('.')[0].length > MAX_TOTAL_DIGITS) {
    return 'invalid';
  }
  return /^0+(\.0{1,2})?$/.test(text) ? 'zero-undeclared' : 'ok';
}

export function lineValueMessage(state: LineValueState): string | null {
  switch (state) {
    case 'pending':
      return 'Pendiente: ingresa un valor o declara costo cero.';
    case 'invalid':
      return 'Ingresa un importe válido con hasta 2 decimales.';
    case 'zero-undeclared':
      return 'Un costo cero debe declararse explícitamente.';
    default:
      return null;
  }
}

/** Texto decimal → entero escalado (`"12.5"`, 4 → 125000n); `null` si no es un decimal simple válido. */
function scaled(text: string, decimals: number, pattern: RegExp): bigint | null {
  const value = text.trim();
  if (!pattern.test(value)) {
    return null;
  }
  const [whole, fraction = ''] = value.split('.');
  return BigInt(whole + fraction.padEnd(decimals, '0'));
}

/**
 * Costo unitario derivado (valor ÷ cantidad) a 6 decimales con redondeo «half up», en aritmética entera, igual que
 * el servidor. `null` si falta el valor o la cantidad. Al guardar manda el servidor.
 */
export function previewUnitCost(totalValue: string, declaredZero: boolean, quantity: string): string | null {
  if (lineValueState(totalValue, declaredZero) !== 'ok') {
    return null;
  }
  const cents = declaredZero ? BigInt(0) : scaled(totalValue, 2, MONEY_PATTERN);
  const units = scaled(quantity, 4, QUANTITY_PATTERN);
  if (cents === null || units === null || units === BigInt(0)) {
    return null;
  }
  // (centavos / 100) / (unidades / 10^4) * 10^6 = centavos * 10^8 / unidades
  const numerator = cents * BigInt(10) ** BigInt(8);
  const rounded = (numerator * BigInt(2) + units) / (units * BigInt(2));
  const digits = rounded.toString().padStart(7, '0');
  return `${digits.slice(0, -6)}.${digits.slice(-6)}`;
}
