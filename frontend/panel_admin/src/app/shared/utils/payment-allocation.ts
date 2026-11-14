import { fromCents, toCents } from '../models/receivable';

export interface AllocatableLine {
  line_id: string;
  balance: string;
}

export interface Allocation {
  line_id: string;
  cents: number;
}

/**
 * Reparto automático (INV-03): recorre las líneas en el orden de la proforma y asigna `min(restante, saldo)`.
 * Solo propone: el servidor valida las imputaciones explícitas que reciba.
 */
export function autoAllocate(amountCents: number, lines: readonly AllocatableLine[]): Allocation[] {
  let remaining = Math.max(0, amountCents);
  const result: Allocation[] = [];
  for (const line of lines) {
    const part = Math.min(remaining, toCents(line.balance) ?? 0);
    if (part > 0) result.push({ line_id: line.line_id, cents: part });
    remaining -= part;
  }
  return result;
}

/** «50 %» del saldo (INV-04): redondeo al centavo hacia arriba. */
export function halfOf(balanceCents: number): number {
  return Math.ceil(Math.max(0, balanceCents) / 2);
}

export function totalCents(lines: readonly AllocatableLine[]): number {
  return lines.reduce((sum, line) => sum + (toCents(line.balance) ?? 0), 0);
}

export function formatCents(cents: number): string {
  return fromCents(cents);
}
