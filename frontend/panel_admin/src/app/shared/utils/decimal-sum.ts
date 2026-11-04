const DECIMAL = /^(-?)(\d+)(?:\.(\d+))?$/;

/**
 * Suma importes que la API entrega como texto decimal ("120.50") sin pasar por coma flotante: trabaja con enteros
 * en la unidad mínima. Devuelve texto con al menos 2 decimales ("0.00" si no hay valores). Los valores vacíos o con
 * formato inválido se ignoran.
 */
export function sumMoney(values: readonly string[]): string {
  const parsed = values.map(parse).filter((p): p is Parsed => p !== null);
  const scale = Math.max(2, ...parsed.map((p) => p.fraction.length));
  const total = parsed.reduce((acc, p) => acc + p.sign * BigInt(p.whole + p.fraction.padEnd(scale, '0')), 0n);
  const negative = total < 0n;
  const digits = (negative ? -total : total).toString().padStart(scale + 1, '0');
  const whole = digits.slice(0, digits.length - scale);
  const fraction = digits.slice(digits.length - scale);
  return `${negative ? '-' : ''}${whole}.${fraction}`;
}

interface Parsed {
  sign: 1n | -1n;
  whole: string;
  fraction: string;
}

function parse(value: string): Parsed | null {
  const match = DECIMAL.exec(value.trim());
  if (!match) {
    return null;
  }
  return { sign: match[1] ? -1n : 1n, whole: match[2], fraction: match[3] ?? '' };
}
