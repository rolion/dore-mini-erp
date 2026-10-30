/**
 * Importes de una compra en el navegador, solo para mostrar mientras se edita. Replican la regla del servidor
 * (subtotal = cantidad × precio redondeado a 2 decimales, mitad hacia arriba; total = suma de subtotales) con
 * aritmética entera: el dinero nunca pasa por `number`. Tras guardar manda el valor del servidor.
 */

const QUANTITY_SCALE = 3;
const PRICE_SCALE = 2;
const PLAIN_DECIMAL = /^\d+(\.\d+)?$/;

/** Convierte un decimal simple a entero escalado, o `null` si no es un decimal válido con esos decimales. */
function toScaled(text: string, scale: number): bigint | null {
  const value = text.trim();
  if (!PLAIN_DECIMAL.test(value)) return null;
  const [whole, fraction = ''] = value.split('.');
  if (fraction.length > scale) return null;
  return BigInt(whole + fraction.padEnd(scale, '0'));
}

function format(cents: bigint): string {
  const digits = cents.toString().padStart(3, '0');
  return `${digits.slice(0, -2)}.${digits.slice(-2)}`;
}

/** Subtotal en centavos, o `null` si la cantidad o el precio no son válidos todavía. */
export function subtotalCents(quantity: string, unitPrice: string): bigint | null {
  const q = toScaled(quantity, QUANTITY_SCALE);
  const p = toScaled(unitPrice, PRICE_SCALE);
  if (q === null || p === null || q === 0n) return null;
  const scale = 10n ** BigInt(QUANTITY_SCALE); // q y p llevan 3 y 2 decimales; el resultado, 5
  const product = q * p;
  return (product + scale / 2n) / scale;
}

/** Subtotal como texto con 2 decimales, o `null` si la línea aún no es válida. */
export function lineSubtotal(quantity: string, unitPrice: string): string | null {
  const cents = subtotalCents(quantity, unitPrice);
  return cents === null ? null : format(cents);
}

/** Total de las líneas válidas, como texto con 2 decimales. */
export function purchaseTotal(lines: readonly { quantity: string; unitPrice: string }[]): string {
  let total = 0n;
  for (const line of lines) {
    total += subtotalCents(line.quantity, line.unitPrice) ?? 0n;
  }
  return format(total);
}

/** Cantidad válida (> 0, hasta 3 decimales y entera si la unidad no admite fracciones). */
export function isValidQuantity(text: string, allowsFractions = true): boolean {
  const scaled = toScaled(text, QUANTITY_SCALE);
  if (scaled === null || scaled === 0n) return false;
  return allowsFractions || scaled % 1000n === 0n;
}

/** Precio unitario válido (≥ 0, hasta 2 decimales). */
export function isValidPrice(text: string): boolean {
  return toScaled(text, PRICE_SCALE) !== null;
}
