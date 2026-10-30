/** Aritmética de importes en centavos enteros (BigInt): replica la regla del servidor, sin `float`. */

const MONEY = /^\d+(\.\d{1,2})?$/;

/** Centavos de un importe de texto con hasta 2 decimales, o `null` si no es un importe válido. */
export function toCents(text: string): bigint | null {
  const value = text.trim();
  if (!MONEY.test(value)) return null;
  const [whole, fraction = ''] = value.split('.');
  return BigInt(whole) * 100n + BigInt(fraction.padEnd(2, '0'));
}

/** Texto con 2 decimales a partir de centavos. */
export function fromCents(cents: bigint): string {
  const abs = cents < 0n ? -cents : cents;
  const sign = cents < 0n ? '-' : '';
  return `${sign}${abs / 100n}.${String(abs % 100n).padStart(2, '0')}`;
}

/** Mensaje de error del monto frente al saldo vigente, o `null` si el monto es pagable. */
export function amountError(text: string, balance: string): string | null {
  if (!text.trim()) return 'El monto es obligatorio.';
  const cents = toCents(text);
  if (cents === null) return 'Ingresa un monto válido con hasta 2 decimales.';
  if (cents <= 0n) return 'El monto debe ser mayor a cero.';
  const limit = toCents(balance);
  if (limit !== null && cents > limit) return `El monto no puede superar el saldo pendiente (Bs ${balance}).`;
  return null;
}
