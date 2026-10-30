/**
 * Cantidades de una recepción en el navegador, solo para validar y mostrar mientras se escribe. Replican la regla
 * del servidor (cantidad > 0, hasta 3 decimales, entera si la unidad no admite fracciones, sin superar el
 * pendiente) con aritmética entera. Tras confirmar manda el servidor.
 */

const SCALE = 3;
const PLAIN_DECIMAL = /^\d+(\.\d+)?$/;

/** Convierte un decimal simple a entero escalado (3 decimales), o `null` si no lo es o trae más decimales. */
function toScaled(text: string): bigint | null {
  const value = text.trim();
  if (!PLAIN_DECIMAL.test(value)) return null;
  const [whole, fraction = ''] = value.split('.');
  if (fraction.length > SCALE) return null;
  return BigInt(whole + fraction.padEnd(SCALE, '0'));
}

function format(scaled: bigint): string {
  const digits = scaled.toString().padStart(SCALE + 1, '0');
  return `${digits.slice(0, -SCALE)}.${digits.slice(-SCALE)}`;
}

/** Cantidad positiva y válida como texto con 3 decimales, o `null` (vacío, cero o inválida). */
export function positiveQuantity(text: string): string | null {
  const scaled = toScaled(text);
  return scaled !== null && scaled > 0n ? format(scaled) : null;
}

/** `true` si el texto es una cantidad mayor a cero (se enviará); vacío o cero se omiten. */
export function isReceivable(text: string): boolean {
  return positiveQuantity(text) !== null;
}

/**
 * Mensaje de error de lo escrito en «A recibir», o `null` si está bien o vacío/cero (la línea se omite).
 * `pending` es el pendiente de la línea (texto decimal del servidor).
 */
export function quantityError(text: string, pending: string, allowsFractions: boolean): string | null {
  const value = text.trim();
  if (value === '') return null;
  if (value.startsWith('-')) return 'La cantidad no puede ser negativa.';
  if (!PLAIN_DECIMAL.test(value)) return 'Ingresa un número válido.';
  const scaled = toScaled(value);
  if (scaled === null) return 'Admite como máximo 3 decimales.';
  if (scaled === 0n) return null;
  if (!allowsFractions && scaled % 1000n !== 0n) return 'La unidad no admite fracciones: usa una cantidad entera.';
  const limit = toScaled(pending) ?? 0n;
  if (scaled > limit) return `No puede superar el pendiente (${pending}).`;
  return null;
}

/** Pendiente tras recibir `quantity` (no baja de cero), como texto con 3 decimales. */
export function pendingAfter(pending: string, quantity: string): string {
  const left = (toScaled(pending) ?? 0n) - (toScaled(quantity) ?? 0n);
  return format(left > 0n ? left : 0n);
}

/** `true` si el texto decimal es mayor a cero. */
export function isPositive(text: string): boolean {
  const scaled = toScaled(text);
  return scaled !== null && scaled > 0n;
}
