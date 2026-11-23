/**
 * Importes del pedido en el navegador, solo para mostrar mientras se arma. Replican la regla del servidor
 * (subtotal de línea = precio × cantidad entera; subtotal = suma; total = subtotal − descuento; el descuento no puede
 * superar el subtotal ni el % máximo configurado) con aritmética entera en centavos: el dinero nunca pasa por
 * `number`. Tras crear manda el valor del servidor.
 */

const PLAIN_DECIMAL = /^\d+(\.\d{1,2})?$/;

/** Decimal simple con hasta 2 decimales → centavos, o `null` si no es válido. */
export function toCents(text: string): bigint | null {
  const value = text.trim();
  if (!PLAIN_DECIMAL.test(value)) return null;
  const [whole, fraction = ''] = value.split('.');
  return BigInt(whole + fraction.padEnd(2, '0'));
}

export function formatCents(cents: bigint): string {
  const digits = (cents < 0n ? -cents : cents).toString().padStart(3, '0');
  return `${cents < 0n ? '-' : ''}${digits.slice(0, -2)}.${digits.slice(-2)}`;
}

/** Subtotal de una línea en centavos (precio × cantidad), o `null` si el precio o la cantidad no son válidos. */
export function lineCents(unitPrice: string, quantity: number): bigint | null {
  const price = toCents(unitPrice);
  if (price === null || !Number.isInteger(quantity) || quantity < 1) return null;
  return price * BigInt(quantity);
}

export function lineSubtotal(unitPrice: string, quantity: number): string | null {
  const cents = lineCents(unitPrice, quantity);
  return cents === null ? null : formatCents(cents);
}

/** Suma de las líneas válidas, en centavos. */
export function subtotalCents(lines: readonly { unitPrice: string; quantity: number }[]): bigint {
  return lines.reduce((total, line) => total + (lineCents(line.unitPrice, line.quantity) ?? 0n), 0n);
}

/** Descuento máximo permitido (% del subtotal, hasta 2 decimales) como texto en Bs, redondeado hacia abajo. */
export function maxDiscountAmount(subtotal: bigint, percent: string): string {
  const scaled = toCents(percent);
  return formatCents(scaled === null ? subtotal : (subtotal * scaled) / 10000n);
}

export type DiscountProblem = 'invalid' | 'above_subtotal' | 'above_percent';

/** Motivo por el que el descuento no es válido para ese subtotal y tope, o `null` si lo es (vacío = sin descuento). */
export function discountProblem(discount: string, subtotal: bigint, percent: string): DiscountProblem | null {
  if (discount.trim() === '') return null;
  const cents = toCents(discount);
  if (cents === null) return 'invalid';
  if (cents > subtotal) return 'above_subtotal';
  const scaled = toCents(percent);
  if (scaled !== null && cents * 10000n > subtotal * scaled) return 'above_percent';
  return null;
}

/** Total = subtotal − descuento (el descuento inválido cuenta como cero). */
export function totalCents(subtotal: bigint, discount: string): bigint {
  const cents = discount.trim() === '' ? 0n : (toCents(discount) ?? 0n);
  return subtotal - (cents > subtotal ? 0n : cents);
}
